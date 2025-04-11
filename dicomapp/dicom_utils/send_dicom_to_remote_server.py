from dicomapp.models import *
from logging import getLogger
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from django.conf import settings
import pydicom
from deidapp.models import *
from api_client.models import *
import pandas as pd
import glob
import hashlib
import zipfile
from api_client.api_utils.dicom_export import DicomExporter
from api_client.api_utils.scan_dicom import compute_file_checksum

logger = getLogger(__name__)

def send_dicom_to_remote_server(deidentification_result: dict):
    """
    This function runs after the deidentify_dicom_series task has been completed.
    It will take as input the folders where the deidentified DICOM series are located after successful deidentification.
    It will then send the DICOM series to the remote server. 

    Args:
        deidentification_result (dict): Dictionary returned by deidentify_dicom_series containing:
            - status (success, partial_failure, or failure)
            - task_id: The id of the celery task
            - message (message to be displayed)
            - series_folder_paths: Dictionary with keys 'successful' and 'failed' containing lists of paths where series folders were moved
            - deidentification_status: true if the series is ready for deidentification, false otherwise
            - failed_series: List of series IDs that failed to process
            - successful_series: List of series IDs that were processed successfully
    """
    temp_folder = None
    try:
        task_id = deidentification_result.get('task_id', 'unknown')
        logger.info(f"Task {task_id}: Starting DICOM series transfer to remote server")

        # Validate input
        if not isinstance(deidentification_result, dict):
            raise ValueError("Invalid input format: expected dictionary")

        if not deidentification_result.get('series_folder_paths'):
            raise ValueError("No series folder paths provided")

        # Setup paths using os.path
        base_dir = settings.BASE_DIR
        temp_folder = os.path.join(base_dir, 'folders', 'folder_temp')
        archive_folder = os.path.join(base_dir, 'folders', 'folder_archive')



        transfer_results = []
        
        # Get successful paths from deidentification results
        successful_paths = deidentification_result['series_folder_paths'].get('successful', [])
        if not successful_paths:
            logger.warning(f"Task {task_id}: No successful paths found in deidentification results")
            return {
                "status": "error",
                "message": "No successful paths found in deidentification results",
                "transfer_results": [],
                "original_processing": deidentification_result
            }
            
        logger.info(f"Task {task_id}: Found {len(successful_paths)} successful paths to process")
        
        # Process each successful series
        for series_path in successful_paths:
            try:
                logger.info(f"Processing series at path: {series_path}")

                # Ensure required folders exist Create if required
                os.makedirs(temp_folder, exist_ok=True)
                os.makedirs(archive_folder, exist_ok=True)
                logger.info(f"Created temp folder at {temp_folder} and archive folder at {archive_folder}")

                # Verify path exists
                if not os.path.exists(series_path):
                    raise ValueError(f"Series path does not exist: {series_path}")

                # Get DICOM files
                dicom_files = glob.glob(os.path.join(series_path, '*.dcm'))
                if not dicom_files:
                    raise ValueError(f"No DICOM files found in {series_path}")

                # Read first DICOM file for UIDs
                first_dicom = dicom_files[0]
                ds = pydicom.dcmread(first_dicom, stop_before_pixels=True)
                series_uid = ds.SeriesInstanceUID
                study_uid = ds.StudyInstanceUID
                logger.info(f"Series UID: {series_uid}, Study UID: {study_uid}")

                # Get client name from settings
                client_system_settings = SystemSettings.load()
                client_name = client_system_settings.client_id
                logger.info(f"Client name: {client_name}")
                client_name = ''.join(c for c in client_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                                    if c.isalnum() or c in '_-')

                # Create zip file
                zip_path = os.path.join(temp_folder, f"{client_name}_{series_uid}.zip")
                logger.info(f"Creating zip file at {zip_path}")

                # Create zip with all files
                with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                    for file_name in os.listdir(series_path):
                        file_path = os.path.join(series_path, file_name)
                        if os.path.isfile(file_path):
                            zf.write(file_path, file_name)

                # Verify zip integrity
                if os.path.getsize(zip_path) == 0:
                    raise zipfile.BadZipFile("Empty zip file created")

                # Compute checksum
                zip_checksum = compute_file_checksum(zip_path)
                logger.info(f"Computed checksum for {zip_path}: {zip_checksum}")

                # Initiate transfer
                exporter = DicomExporter()
                transfer_result = exporter.initiate_transfer(
                    zip_path,
                    study_uid,
                    series_uid,
                    zip_checksum
                )

                # Move files to archive
                archive_study_dir = os.path.join(archive_folder, study_uid)
                archive_series_dir = os.path.join(archive_study_dir, series_uid)
                os.makedirs(archive_series_dir, exist_ok=True)

                # Move all files to archive
                for file_name in os.listdir(series_path):
                    if os.path.isfile(os.path.join(series_path, file_name)):
                        source_path = os.path.join(series_path, file_name)
                        target_path = os.path.join(archive_series_dir, file_name)
                        shutil.move(source_path, target_path)

                # Remove empty series folder if possible
                if not os.listdir(series_path):
                    os.rmdir(series_path)

                transfer_results.append({
                    "series_id": os.path.basename(series_path),
                    "status": "success",
                    "study_uid": study_uid,
                    "series_uid": series_uid,
                    "transfer_result": transfer_result,
                    "archive_path": archive_series_dir
                })

            except Exception as e:
                logger.error(f"Error processing series {series_path}: {str(e)}")
                transfer_results.append({
                    "series_id": os.path.basename(series_path),
                    "status": "error",
                    "message": str(e),
                    "original_path": series_path
                })
            finally:
                # Clean up zip file and temp folder immediately after processing each series
                try:
                    # Clean up zip file
                    if zip_path and os.path.exists(zip_path):
                        os.remove(zip_path)
                        logger.info(f"Task {task_id}: Cleaned up zip file for series {os.path.basename(series_path)}")
                    
                    # Clean up temp folder if it's empty
                    if temp_folder and os.path.exists(temp_folder):
                        if not os.listdir(temp_folder):
                            os.rmdir(temp_folder)
                            logger.info(f"Task {task_id}: Cleaned up empty temp folder after processing series {os.path.basename(series_path)}")
                except Exception as e:
                    logger.warning(f"Task {task_id}: Warning during cleanup for series {os.path.basename(series_path)}: {str(e)}")

        # Return summary of all transfers
        return {
            "status": "success" if any(r['status'] == 'success' for r in transfer_results) else "error",
            "transfer_results": transfer_results,
            "original_processing": deidentification_result,
            "archive_folder": archive_folder
        }

    except Exception as e:
        logger.error(f"Task {task_id}: Error during series transfer: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "original_processing": deidentification_result
        }
    finally:
        # Final cleanup of temp folder if it exists and is empty
        if temp_folder and os.path.exists(temp_folder):
            try:
                if not os.listdir(temp_folder):
                    os.rmdir(temp_folder)
                    logger.info(f"Task {task_id}: Successfully cleaned up temp folder after all processing")
            except Exception as e:
                logger.warning(f"Task {task_id}: Warning during final temp folder cleanup: {str(e)}")
