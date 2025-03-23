import os
from celery import shared_task, chain
from django.conf import settings
import logging
from django.utils import timezone
from deidapp.dicomutils.deidentify_dicom import deidentify_dicom
from deidapp.models import *

# Create a dedicated logger for deidentification tasks
logger = logging.getLogger('deidapp_logs')
# Add Celery's logger
celery_logger = logging.getLogger('celery.task')


@shared_task
def deidentify_dicom():
    """
    This task will deidentify DICOM files in the folder_for_deidentification folder and save the processed files in the folder_post_deidentification folder. It will also create the folder_for_deidentification folder if it doesn't exist.
    """
    try:
        # Create the folder called folder_for_deidentification if it doesn't exist
        if not os.path.exists(os.path.join(settings.BASE_DIR, 'folder_for_deidentification')):
            os.makedirs(os.path.join(settings.BASE_DIR, 'folder_for_deidentification'))

        # Create the folder_post_deidentification folder if it doesn't exist
        if not os.path.exists(os.path.join(settings.BASE_DIR, 'folder_post_deidentification')):
            os.makedirs(os.path.join(settings.BASE_DIR, 'folder_post_deidentification'))

        logger.info("Starting DICOM deidentification")
        deidentify_dicom()
        logger.info("DICOM deidentification completed successfully")
    except Exception as e:
        logger.error(f"Error during DICOM deidentification: {str(e)}")
        raise e

@shared_task
def reidentify_rtstruct():
    """
    """
    pass