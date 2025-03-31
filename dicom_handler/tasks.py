import os
import shutil
from pathlib import Path
from celery import shared_task, chain
from django.conf import settings
from dicom_handler.dicomutils.copydicom import *
from dicom_handler.dicomutils.dicomseriesprocessing import dicom_series_separation
from dicom_handler.dicomutils.dicomseriesprocessing import read_dicom_metadata  
from dicom_handler.dicomutils.exportrtstruct import *
from deidapp.dicomutils.deidentify_dicom import *
from pathlib import Path
import zipfile
import pydicom
import logging
from dicom_handler.models import DicomPathConfig, CopyDicom, ProcessingStatusChoices
from django.utils import timezone
from api_client.api_utils.scan_dicom import scan_dicom_folder, compute_file_checksum
from api_client.api_utils.dicom_export import *
from api_client.models import *

# Create a dedicated logger for DICOM handler tasks
logger = logging.getLogger('dicom_handler_logs')
# Add Celery's logger
celery_logger = logging.getLogger('celery.task')

@shared_task
def test_celery_logging_task():
    """
    This is a simple task to test that Celery is working and logging properly.
    """
    try:
        logger.debug("Debug message from test_celery_logging_task")
        logger.info("Info message from test_celery_logging_task")
        logger.warning("Warning message from test_celery_logging_task")
        celery_logger.info("Celery logger test message")
        return True
    except Exception as e:
        logger.error(f"Error in test_celery_logging_task: {str(e)}")
        return False

@shared_task
def copy_dicom():
    '''
    Automatically copy DICOM files from the datastore path defined in DicomPathConfig
    to the import_dicom path.
    
    After completion, triggers dicom_series_separation and read_dicom_metadata tasks in sequence.
    '''
    try:
        # Get the path configuration
        path_config = DicomPathConfig.get_instance()
        logger.info(f"Path configuration: {path_config}")
        source_path = path_config.get_safe_path()
        logger.info(f"Source path: {source_path}")
        if not source_path:
            raise ValueError("No datastore path configured")
            
        destination_path = os.path.join(settings.BASE_DIR, 'folder_for_dicom_import')
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
        logger.info(f"Destination path created: {destination_path}")
        
        # Log the fact that the task has started
        celery_logger.info("copy_dicom task started")
        logger.info(f"Starting copydicom task with source={source_path}, destination={destination_path}")
        
        # Call the copydicom function
        copydicom(
            sourcedir=str(source_path),
            destinationdir=destination_path
            )
        
        logger.info("Copy DICOM task completed successfully")
        
        # Trigger the next tasks with the import_dicom path
        logger.info(f"Triggering dicom_series_separation_task with import_dicom path: {destination_path}")
        dicom_series_separation_task.delay()
        
        return True
    except Exception as e:
        logger.error(f"Error in copy_dicom task: {str(e)}")
        celery_logger.error(f"copy_dicom task failed with error: {str(e)}")
        return False

@shared_task
def dicom_series_separation_task(import_dicom_path=None):
    '''
    Automatically separate DICOM files from the import_dicom path into separate series folders.
    
    Args:
        import_dicom_path (str, optional): Path to the directory containing imported DICOM files.
            If not provided, will use the path from DicomPathConfig.
            
    This task:
    1. Takes DICOM files from the copied folders in CopyDicom model with COPIED status
    2. Separates them into series-specific folders in the processing folder
    3. Updates the processing status to PROCESSED
    4. Triggers read_dicom_metadata_task for each separated series folder
    '''
    try:
        # Processing folder path is a relative path to the Base Directory
        processing_folder_path = os.path.join(settings.BASE_DIR, 'folder_dicom_processing')

        # Create the processing folder if it doesn't exist
        if not os.path.exists(processing_folder_path):
            os.makedirs(processing_folder_path)
            logger.info(f"Processing folder created: {processing_folder_path}")

        # We will get the list of all folders in the CopyDicom model with processing_status as COPIED
        copied_folders = CopyDicom.objects.filter(processing_status=ProcessingStatusChoices.COPIED.value)
        logger.info(f"Found {len(copied_folders)} folders with COPIED status")
        
        for folder in copied_folders:
            logger.info(f"Processing folder: {folder.destinationdirname}")
            # We get the destination directory path from the CopyDicom model
            import_dicom_path = folder.destinationdirname
            logger.info(f"Import DICOM path: {import_dicom_path}")
            # Call the dicom_series_separation function and capture the returned series paths
            separated_series_dirs = dicom_series_separation(
                sourcedir=import_dicom_path,
                processeddir=processing_folder_path
            )
            
            # Ensure processing status is updated to PROCESSED
            logger.info(f"Updating processing status to PROCESSED for {folder.id}-{folder.destinationdirname}")
            CopyDicom.objects.filter(id=folder.id).update(processing_status=ProcessingStatusChoices.PROCESSED.value)
            logger.info(f"Processing status updated to PROCESSED for {folder.destinationdirname}")
            logger.info(f"DICOM series separation task completed successfully for {import_dicom_path}")
            logger.info(f"Created {len(separated_series_dirs)} series directories")
            
            # Trigger the read_dicom_metadata_task for each separated series directory
            for i, series_dir in enumerate(separated_series_dirs):
                logger.info(f"Queueing read_dicom_metadata_task for series directory: {series_dir}")
                
                # Use apply_async with additional options for more control
                task = read_dicom_metadata_task.apply_async(
                    args=[series_dir],
                    countdown=i*2,  # Stagger execution by 2 seconds per task to prevent resource contention
                    priority=10,  # Set priority (higher numbers = higher priority)
                    expires=3600*24  # Task expires after 24 hours if not executed
                )
                logger.info(f"Task dispatched with ID: {task.id}")
                logger.info(f"Task for series {i+1}/{len(separated_series_dirs)} queued with {i*2}s countdown")
            
        return True
    except Exception as e:
        logger.error(f"Error in dicom_series_separation task: {str(e)}")
        return False
    
@shared_task
def read_dicom_metadata_task(dicom_series_path=None):
    '''
    Read DICOM metadata from a specific series folder and process it according to rules.
    
    This task:
    1. Processes a single DICOM series folder passed from dicom_series_separation_task
    2. Validates the existence of the directory
    
    Args:
        dicom_series_path (str): Path to the specific DICOM series folder to process.
            Each path represents a single series directory containing DICOM files.
            
    Returns:
        success: bool, True if processing was successful, False otherwise
        deidentification_path: str, Path to the deidentified DICOM series folder. If series is not ready for deidentification, the path will be the unprocessed folder.
    '''
    start_time = timezone.now()
    task_id = read_dicom_metadata_task.request.id if hasattr(read_dicom_metadata_task, 'request') else 'unknown'
    
    try:
        logger.info(f"Task {task_id}: Starting processing of DICOM series")
        
        # Validate input parameter
        if dicom_series_path is None:
            logger.error(f"Task {task_id}: No DICOM series path provided")
            return False
        
        # Ensure the path is a string
        if not isinstance(dicom_series_path, str):
            logger.error(f"Task {task_id}: Invalid path type: {type(dicom_series_path)}")
            return False
        
        logger.info(f"Task {task_id}: Processing DICOM series path: {dicom_series_path}")

        # Verify the specific DICOM series folder exists
        if not os.path.exists(dicom_series_path):
            logger.error(f"Task {task_id}: DICOM series path does not exist: {dicom_series_path}")
            return False
        
        # Verify the path contains DICOM files
        dicom_files = [f for f in os.listdir(dicom_series_path) 
                       if os.path.isfile(os.path.join(dicom_series_path, f)) 
                       and not f.endswith('.yml')]
        
        if not dicom_files:
            logger.error(f"Task {task_id}: No DICOM files found in directory: {dicom_series_path}")
            return False
            
        logger.info(f"Task {task_id}: Found {len(dicom_files)} DICOM files to process")

        # Prepare destination directories
        unprocessed_folder_path = os.path.join(settings.BASE_DIR, 'folder_unprocessed_dicom')
        deidentified_folder_path = os.path.join(settings.BASE_DIR, 'folder_for_deidentification')

        # Create the unprocessed folder if it doesn't exist
        if not os.path.exists(unprocessed_folder_path):
            os.makedirs(unprocessed_folder_path)
            logger.info(f"Task {task_id}: Unprocessed folder created: {unprocessed_folder_path}")

        # Create the deidentified folder if it doesn't exist
        if not os.path.exists(deidentified_folder_path):
            os.makedirs(deidentified_folder_path)
            logger.info(f"Task {task_id}: Deidentified folder created: {deidentified_folder_path}")

        # Call the read_dicom_metadata function
        try:
            result = read_dicom_metadata(
                dicom_series_path=dicom_series_path,
                unprocess_dicom_path=unprocessed_folder_path,
                deidentified_dicom_path=deidentified_folder_path
            )
            
            processing_time = timezone.now() - start_time
            logger.info(f"Task {task_id}: DICOM metadata reading completed in {processing_time.total_seconds():.2f} seconds for: {dicom_series_path}")
            
            # Add a return of values from the read_dicom_metadata function
            if result['success']:
                logger.info(f"Task {task_id}: DICOM metadata processing successful for {dicom_series_path}")
                chain(
                    deidentify_series_task.s(result),
                    transfer_deidentified_series_task.s()
                ).apply_async()
            else:
                logger.error(f"Task {task_id}: DICOM metadata processing failed for {dicom_series_path}")
            return result
        except Exception as e:
            logger.error(f"Task {task_id}: Error in read_dicom_metadata function: {str(e)}")
            # Consider additional error handling here if needed
            return {"success": False, "deidentification_path": None}
            
    except Exception as e:
        processing_time = timezone.now() - start_time
        logger.error(f"Task {task_id}: Error in read_dicom_metadata task after {processing_time.total_seconds():.2f} seconds for {dicom_series_path}: {str(e)}")
        return {"success": False, "deidentification_path": None}

@shared_task
def deidentify_series_task(result):
    """
    This task processes a single series for deidentification.
    It only runs if the previous task (read_dicom_metadata) was successful.
    
    Args:
        result (dict): Dictionary containing 'success' and 'deidentification_path' from read_dicom_metadata
        
    Returns:
        dict: Results of the deidentification process
    """
    task_id = deidentify_series_task.request.id if hasattr(deidentify_series_task, 'request') else 'unknown'
    
    try:
        # Check if previous task was successful and we have a valid path
        if not result.get('success') or not result.get('deidentification_path'):
            logger.warning(f"Task {task_id}: Skipping deidentification - previous task failed or no path provided")
            return {
                "status": "skipped",
                "message": "Previous task failed or no path provided",
                "details": []
            }
            
        # Check if the post-deidentification directory exists
        processed_dir = os.path.join(settings.BASE_DIR, 'folder_post_deidentification')
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir, exist_ok=True)
            logger.info(f"Task {task_id}: Created post-deidentification directory: {processed_dir}")
        
        # Log the actual path we're processing
        logger.info(f"Task {task_id}: Starting deidentification for path: {result['deidentification_path']}")
        
        # Deidentify the specific series directly
        deidentification_result = deidentify_dicom(
            dicom_dir=result['deidentification_path'],
            processed_dir=processed_dir
        )
        
        logger.info(f"Task {task_id}: Deidentification result: {deidentification_result}")
        
        # Create a result structure that's compatible with the transfer task
        if deidentification_result.get("status") == "success":
            logger.info(f"Task {task_id}: Deidentification completed successfully")
            
            # Format the result for the next task in the chain
            return {
                "status": "success",
                "details": [
                    {
                        "series_id": os.path.basename(result['deidentification_path']),
                        "status": "success",
                        "deidentified_path": deidentification_result.get("deidentified_path")
                    }
                ],
                "message": "Deidentification completed successfully"
            }
        else:
            logger.warning(f"Task {task_id}: Deidentification failed: {deidentification_result.get('message')}")
            return {
                "status": "error",
                "message": deidentification_result.get("message", "Deidentification failed"),
                "details": []
            }
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error during series deidentification: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "details": []
        }
    

@shared_task
def transfer_deidentified_series_task(deidentification_result):

    """
    Transfer deidentified series to the remote server.
    
    Args:
        deidentification_result (dict): Result from deidentification process containing:
            - status: Overall status of deidentification
            - details: List of processed series details including paths
            
    Returns:
        dict: Results of the transfer process
    """
    task_id = transfer_deidentified_series_task.request.id if hasattr(transfer_deidentified_series_task, 'request') else 'unknown'
    logger.info(f"Task {task_id}: Starting transfer of deidentified series")
    
    try:
        # Validate input
        if not isinstance(deidentification_result, dict):
            raise ValueError("Invalid deidentification result format")
            
        if not deidentification_result.get('details'):
            raise ValueError("No series details found in deidentification result")
            
        # Get required folder paths
        base_dir = settings.BASE_DIR
        temp_folder = os.path.join(base_dir, 'folder_temp')
        archive_folder = os.path.join(base_dir, 'folder_archive')
        
        # Ensure required folders exist
        os.makedirs(temp_folder, exist_ok=True)
        os.makedirs(archive_folder, exist_ok=True)
        
        transfer_results = []
        for series_detail in deidentification_result['details']:
            if series_detail['status'] == 'success' and series_detail.get('deidentified_path'):
                try:
                    deidentified_path = series_detail['deidentified_path']
                    logger.info(f"Processing series at path: {deidentified_path}")
                    
                    # Verify path exists
                    if not os.path.exists(deidentified_path):
                        raise ValueError(f"Deidentified path does not exist: {deidentified_path}")
                    
                    # Get DICOM files
                    dicom_files = [f for f in os.listdir(deidentified_path) 
                                 if f.endswith('.dcm') and os.path.isfile(os.path.join(deidentified_path, f))]
                    
                    if not dicom_files:
                        raise ValueError(f"No DICOM files found in {deidentified_path}")
                    
                    # Read first DICOM file for UIDs
                    first_dicom = os.path.join(deidentified_path, dicom_files[0])
                    ds = pydicom.dcmread(first_dicom, stop_before_pixels=True)
                    series_uid = ds.SeriesInstanceUID
                    study_uid = ds.StudyInstanceUID
                    
                    # Get client name from settings
                    system_settings = SystemSettings.load()
                    client_name = system_settings.client_id
                    client_name = ''.join(c for c in client_name.replace(' ', '_').replace('/', '_').replace('\\', '_') 
                                        if c.isalnum() or c in '_-')
                    
                    # Create zip file
                    zip_path = os.path.join(temp_folder, f"{client_name}_{series_uid}.zip")
                    logger.info(f"Creating zip file at {zip_path}")
                    
                    try:
                        # Create zip with all files
                        with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                            for filename in os.listdir(deidentified_path):
                                file_path = os.path.join(deidentified_path, filename)
                                if os.path.isfile(file_path):
                                    zf.write(file_path, filename)
                            
                            # Verify zip integrity
                            if zf.testzip() is not None:
                                raise zipfile.BadZipFile(f"Corrupt zip file detected")
                        
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
                        
                        for filename in os.listdir(deidentified_path):
                            src_path = os.path.join(deidentified_path, filename)
                            dst_path = os.path.join(archive_series_dir, filename)
                            if os.path.isfile(src_path):
                                shutil.move(src_path, dst_path)
                        
                        # Remove empty series folder if possible
                        if not os.listdir(deidentified_path):
                            os.rmdir(deidentified_path)
                        
                        transfer_results.append({
                            "series_id": series_detail['series_id'],
                            "status": "success",
                            "study_uid": study_uid,
                            "series_uid": series_uid,
                            "transfer_result": transfer_result
                        })
                        
                    finally:
                        # Clean up zip file
                        if os.path.exists(zip_path):
                            os.remove(zip_path)
                            
                except Exception as e:
                    logger.error(f"Error processing series {series_detail['series_id']}: {str(e)}")
                    transfer_results.append({
                        "series_id": series_detail['series_id'],
                        "status": "error",
                        "message": str(e),
                        "original_path": series_detail.get('deidentified_path')
                    })
        
        # Return summary of all transfers
        return {
            "status": "success" if any(r['status'] == 'success' for r in transfer_results) else "error",
            "transfer_results": transfer_results,
            "original_deidentification": deidentification_result
        }
        
    except Exception as e:
        logger.error(f"Task {task_id}: Error during series transfer: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "original_deidentification": deidentification_result
        }
    
@shared_task
def export_rtstruct_task():
    """
    This task will export RTSTRUCT files from the processing folder to the datastore folder.
    It will be triggered after the reidentify_rtstruct task completes.
    """
    try:
        task_id = export_rtstruct_task.request.id
        logger.info(f"[Task ID: {task_id}] Starting RTSTRUCT export task")
        result = export_rtstruct()
        if result:
            logger.info(f"[Task ID: {task_id}] RTSTRUCT export completed successfully")
        else:
            logger.warning(f"[Task ID: {task_id}] RTSTRUCT export completed with issues")
        
        return result
    
    except Exception as e:
        task_id = getattr(export_rtstruct_task, 'request', None)
        task_id = task_id.id if task_id else 'unknown'
        logger.error(f"[Task ID: {task_id}] Error during RTSTRUCT export task: {str(e)}")
        raise e