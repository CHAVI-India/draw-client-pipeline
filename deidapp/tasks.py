import os
from celery import shared_task, chain
from django.conf import settings
import logging
from django.utils import timezone
from deidapp.models import *
from deidapp.dicomutils.deidentify_dicom import process_pending_deidentifications
# Create a dedicated logger for deidentification tasks
logger = logging.getLogger('deidapp_logs')
# Add Celery's logger
celery_logger = logging.getLogger('celery.task')


@shared_task
def deidentify_dicom():
    """
    This task will process all series marked as ready for deidentification in the 
    DicomUnprocessed model. It processes each series folder and saves the results
    in the folder_post_deidentification folder.
    """
    try:
        # Get the current task ID
        
        task_id = deidentify_dicom.request.id
        
        # Create the folder_post_deidentification folder if it doesn't exist
        processed_dir = os.path.join(settings.BASE_DIR, 'folder_post_deidentification')
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)
        
        logger.info(f"[Task ID: {task_id}] Starting DICOM deidentification batch task")
        results = process_pending_deidentifications(processed_dir=processed_dir)
        
        if results["status"] == "success":
            logger.info(f"[Task ID: {task_id}] DICOM deidentification batch completed successfully")
        else:
            logger.warning(f"[Task ID: {task_id}] DICOM deidentification completed with issues: {results['message']}")
            
        return results
        
    except Exception as e:
        task_id = getattr(deidentify_dicom, 'request', None)
        task_id = task_id.id if task_id else 'unknown'
        logger.error(f"[Task ID: {task_id}] Error during DICOM deidentification task: {str(e)}")
        raise e

@shared_task
def reidentify_rtstruct():
    """
    """
    pass