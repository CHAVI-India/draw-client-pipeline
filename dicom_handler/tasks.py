import os
from celery import shared_task, chain
from django.conf import settings
from dicom_handler.dicomutils.copydicom import *
from dicom_handler.dicomutils.dicomseriesprocessing import dicom_series_separation
from dicom_handler.dicomutils.dicomseriesprocessing import read_dicom_metadata  
from dicom_handler.dicomutils.exportrtstruct import *
import logging
from dicom_handler.models import DicomPathConfig, CopyDicom, ProcessingStatusChoices
from django.utils import timezone


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
        destination_path = os.path.join(settings.BASE_DIR, 'folder_for_dicom_import')
        if not os.path.exists(destination_path):
            os.makedirs(destination_path)
        logger.info(f"Destination path created: {destination_path}")
        
        # Log the fact that the task has started
        celery_logger.info("copy_dicom task started")
        logger.info(f"Starting copydicom task with source={path_config.datastorepath}, destination={destination_path}")
        
        # Call the copydicom function
        copydicom(
            sourcedir=path_config.datastorepath,
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
    3. Creates DicomUnprocessed records for the series
    4. Moves the series folder to either the unprocessed or deidentified folder based on processing rules
    
    Args:
        dicom_series_path (str): Path to the specific DICOM series folder to process.
            Each path represents a single series directory containing DICOM files.
            
    Returns:
        bool: True if processing was successful, False otherwise
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
            read_dicom_metadata(
                dicom_series_path=dicom_series_path,
                unprocess_dicom_path=unprocessed_folder_path,
                deidentified_dicom_path=deidentified_folder_path
            )
            
            processing_time = timezone.now() - start_time
            logger.info(f"Task {task_id}: DICOM metadata reading completed in {processing_time.total_seconds():.2f} seconds for: {dicom_series_path}")
            return True
            
        except Exception as e:
            logger.error(f"Task {task_id}: Error in read_dicom_metadata function: {str(e)}")
            # Consider additional error handling here if needed
            return False
            
    except Exception as e:
        processing_time = timezone.now() - start_time
        logger.error(f"Task {task_id}: Error in read_dicom_metadata task after {processing_time.total_seconds():.2f} seconds for {dicom_series_path}: {str(e)}")
        return False

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