from dicomapp.models import *
from logging import getLogger
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from django.conf import settings
import pydicom

logger = getLogger(__name__)



def parse_dicom_date(date_str):
    """
    Parse a DICOM date string (YYYYMMDD format) into a Python date object.
    Returns None if the date string is empty or invalid.
    """
    if not date_str:
        return None
    try:
        # Parse the DICOM date format (YYYYMMDD)
        date_obj = datetime.strptime(date_str, "%Y%m%d").date()
        # Return the date in YYYY-MM-DD format as a string
        return date_obj.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None

    

def series_preparation(input_data: dict) -> dict:
    """
    This function will read the DICOM metadata of the valid DICOM files in the source directory. 
    It will parse each file inside the folder (including any files inside subdirectories)
     
    It will create a dictionary with the following keys:
        - patient_id
        - patient_name
        - age
        - gender
        - scan_date
        - modality
        - study_instance_uid
        - series_instance_uid
        - series_description
        - series_import_directory (path from where the dicom files were copied)
        - series_current_directory (path to the folder inside the target directory where the dicom files were moved to after series separation)
        

    It will save the data in the DicomSeriesProcessingModel table.
    It will update the processing_status to ProcessingStatusChoices.SERIES_SEPARATED.
    It will update the series_state to SeriesState.PROCESSING.
    It will save the task_id of the celery task in the DicomSeriesProcessingModel table.
    It will also create a log entry in the DicomSeriesProcessingLogModel table with a summary of the series processing.
    If a valid dicom file is found it will be moved to the target directory inside a folder whose name is that of the series instance uid.
    If the file is not a valid dicom file it will be not be moved.

    Args:
        input_data (dict): A dictionary containing:
            - status: The status of the operation ('success', 'partial_failure', or 'failure')
            - task_id: The id of the celery task
            - target_paths: List of paths where DICOM directories were copied
            - copy_dicom_task_id: The UUID of the CopyDicomTaskModel entry
            - error: Error message (only present if status is 'failure')

    Returns: A dictionary with the following keys:
        - status (success, partial_failure, or failure)
        - message (message to be displayed)
        - separated_series_path_folders (list of paths to folders where series were successfully separated)
        - series_processing_ids (list of UUIDs of created DicomSeriesProcessingModel entries)
    """
    logger.info("Starting series preparation process")
    
    try:
        # Validate required input
        if not input_data.get('target_paths'):
            logger.warning("No target paths provided")
            return {
                'status': 'failure',
                'message': 'No target paths provided',
                'separated_series_path_folders': [],
                'series_processing_ids': []
            }
        
        # Extract input data with defaults
        source_paths = [str(path) for path in input_data['target_paths']]  # Convert all paths to strings
        task_id = input_data.get('task_id')
        copy_dicom_task_id = input_data.get('copy_dicom_task_id')
        status = input_data.get('status', 'success')
        error = input_data.get('error')
        
        # Handle error status if present
        if status == 'failure':
            logger.warning(f"Input process failed: {error or 'Unknown error'}")
            return {
                'status': 'failure',
                'message': f"Input process failed: {error or 'Unknown error'}",
                'separated_series_path_folders': [],
                'series_processing_ids': []
            }
        
        logger.info(f"Processing {len(source_paths)} source paths")
        processed_paths = []
        processing_errors = []
        
        # Create the directory to store all separated series
        series_directory_string = f"folders/folder_post_series_separation"
        series_directory_path = os.path.join(settings.BASE_DIR, series_directory_string)
        os.makedirs(series_directory_path, exist_ok=True)
        logger.info(f"Created series directory at: {series_directory_path}")
        
        # Dictionary to store series data by SeriesInstanceUID
        series_dict = {}
        # Dictionary to store file paths for each series
        series_files = {}
        # List to store series processing IDs
        series_processing_ids = []
        
        # First pass: collect metadata and file paths
        for source_path in source_paths:
            logger.info(f"Processing directory: {source_path}")
            
            try:
                # Walk through all files in the directory and subdirectories
                for root, _, files in os.walk(source_path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        
                        try:
                            # Try to read the file as DICOM
                            try:
                                dcm = pydicom.dcmread(file_path)
                            except Exception as e:
                                # If it's not a valid DICOM file, just skip it without logging an error
                                continue

                            # Check the modality is CT / MR / PET / US. Allow only those files to be processed.
                            if dcm.Modality not in ['CT', 'MR', 'PET', 'US']:
                                logger.warning(f"File {file_name} is not a CT / MR / PET / US, skipping")
                                continue
                            
                            # Get SeriesInstanceUID
                            series_uid = getattr(dcm, 'SeriesInstanceUID', None)
                            if not series_uid:
                                logger.warning(f"File {file_name} has no SeriesInstanceUID, skipping")
                                continue
                            
                            # Extract required metadata
                            series_data = {
                                'patient_id': getattr(dcm, 'PatientID', ''),
                                'patient_name': getattr(dcm, 'PatientName', ''),
                                'gender': getattr(dcm, 'PatientSex', ''),
                                'scan_date': parse_dicom_date(getattr(dcm, 'StudyDate', '')),
                                'modality': getattr(dcm, 'Modality', ''),
                                'study_instance_uid': getattr(dcm, 'StudyInstanceUID', ''),
                                'series_instance_uid': series_uid,
                                'series_description': getattr(dcm, 'SeriesDescription', ''),
                                'series_import_directory': source_path,
                                'series_current_directory': os.path.join(series_directory_path, series_uid),
                                'final_directory': None,  # Will be set after successful move
                                'copy_dicom_task_id': None  # Will be set after finding the matching task
                            }
                            
                            # Store series data and file path
                            if series_uid not in series_dict:
                                series_dict[series_uid] = series_data
                                series_files[series_uid] = []
                                logger.info(f"Found new series: {series_uid}")
                            
                            series_files[series_uid].append(file_path)
                            logger.info(f"Found DICOM file for series {series_uid}: {file_name}")
                            
                        except Exception as e:
                            logger.error(f"Error processing file {file_name}: {str(e)}")
                            processing_errors.append(f"Error processing file {file_name}: {str(e)}")
                            continue
                
                processed_paths.append(source_path)
                
            except Exception as e:
                logger.error(f"Error processing directory {source_path}: {str(e)}")
                processing_errors.append(f"Error processing directory {source_path}: {str(e)}")
                continue
        
        # Create database entries and move files for each series
        for series_uid, series_data in series_dict.items():
            try:
                # Create series directory if it doesn't exist
                os.makedirs(series_data['series_current_directory'], exist_ok=True)
                
                # Find the matching CopyDicomTaskModel for this series
                copy_dicom_task_instance = None
                if input_data.get('copy_dicom_task_id'):
                    # Find the CopyDicomTaskModel that matches the source path
                    for task_id in input_data['copy_dicom_task_id']:
                        try:
                            task = CopyDicomTaskModel.objects.get(id=task_id)
                            if task.target_directory == series_data['series_import_directory']:
                                copy_dicom_task_instance = task
                                series_data['copy_dicom_task_id'] = task
                                logger.info(f"Found matching CopyDicomTaskModel for series {series_uid}: {task.id}")
                                break
                        except CopyDicomTaskModel.DoesNotExist:
                            continue
                    
                    if not copy_dicom_task_instance:
                        logger.warning(f"No matching CopyDicomTaskModel found for series {series_uid} with import directory {series_data['series_import_directory']}")
                
                # Create the main series processing entry
                series_processing = DicomSeriesProcessingModel.objects.create(
                    patient_id=series_data['patient_id'],
                    patient_name=series_data['patient_name'],
                    gender=series_data['gender'],
                    scan_date=series_data['scan_date'],
                    modality=series_data['modality'],
                    study_instance_uid=series_data['study_instance_uid'],
                    series_instance_uid=series_data['series_instance_uid'],
                    series_description=series_data['series_description'],
                    series_import_directory=series_data['series_import_directory'],
                    series_current_directory=series_data['series_current_directory'],
                    processing_status=ProcessingStatusChoices.SERIES_SEPARATED,
                    series_state=SeriesState.PROCESSING,
                    copy_dicom_task_id=copy_dicom_task_instance
                )
                logger.info(f"Created database entry for series: {series_uid}")
                series_processing_ids.append(str(series_processing.id))

                # Create a log entry with processing summary
                processing_summary = (
                    f"Series {series_uid} processed successfully:\n"
                    f"- Patient ID: {series_data['patient_id']}\n"
                    f"- Study UID: {series_data['study_instance_uid']}\n"
                    f"- Series Description: {series_data['series_description']}\n"
                    f"- Import Directory: {series_data['series_import_directory']}\n"
                    f"- Current Directory: {series_data['series_current_directory']}"
                )

                DicomSeriesProcessingLogModel.objects.create(
                    task_id=task_id,
                    dicom_series_processing_id=series_processing,
                    processing_status=ProcessingStatusChoices.SERIES_SEPARATED,
                    processing_status_message=processing_summary
                )
                logger.info(f"Created log entry for series: {series_uid}")

                # Move files after successful database creation
                for file_path in series_files[series_uid]:
                    try:
                        file_name = os.path.basename(file_path)
                        target_path = os.path.join(series_data['series_current_directory'], file_name)
                        shutil.move(file_path, target_path)
                        logger.info(f"Successfully moved DICOM file: {file_name}")
                    except Exception as e:
                        logger.error(f"Error moving file {file_name}: {str(e)}")
                        processing_errors.append(f"Error moving file {file_name}: {str(e)}")
                        continue

                # Set the final directory after successful move
                series_data['final_directory'] = series_data['series_current_directory']

            except Exception as e:
                logger.error(f"Error processing series {series_uid}: {str(e)}")
                processing_errors.append(f"Error processing series {series_uid}: {str(e)}")
        
        if not processed_paths:
            logger.error("No directories were successfully processed")
            return {
                'status': 'failure',
                'message': 'No directories were successfully processed',
                'separated_series_path_folders': [],
                'series_processing_ids': []
            }
        
        # If we have both successes and failures, return partial_failure
        if processing_errors:
            logger.warning(f"Series preparation completed with some errors: {processing_errors}")
            # Get all final directories where series were successfully processed
            separated_series_path_folders = [series['final_directory'] for series in series_dict.values() if series['final_directory']]
            
            return {
                'status': 'partial_failure',
                'message': f"Series preparation completed with some errors: {', '.join(processing_errors)}",
                'separated_series_path_folders': separated_series_path_folders,
                'series_processing_ids': series_processing_ids
            }
        
        logger.info("Series preparation process completed successfully")
        # Get all final directories where series were successfully processed
        separated_series_path_folders = [series['final_directory'] for series in series_dict.values() if series['final_directory']]
        
        # Delete source directories after successful processing
        if status == 'success':
            for source_path in source_paths:
                try:
                    if os.path.exists(source_path):
                        shutil.rmtree(source_path)
                        logger.info(f"Successfully deleted source directory: {source_path}")
                except Exception as e:
                    logger.error(f"Error deleting source directory {source_path}: {str(e)}")
        
        return {
            'status': 'success',
            'message': 'Series preparation completed successfully',
            'separated_series_path_folders': separated_series_path_folders,
            'series_processing_ids': series_processing_ids
        }
        
    except Exception as e:
        logger.error(f"Failed to complete series preparation: {str(e)}")
        return {
            'status': 'failure',
            'message': f'Error during series preparation: {str(e)}',
            'separated_series_path_folders': [],
            'series_processing_ids': []
        }
