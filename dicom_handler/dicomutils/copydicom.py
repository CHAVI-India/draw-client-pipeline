
# copydicom.py

import os
import shutil
from datetime import datetime, timezone
from dicom_handler.models import CopyDicom
from django.utils import timezone
import logging

# Get logger
logger = logging.getLogger('django_log_lens.client')

def copydicom(sourcedir, destinationdir, timeinterval):
    '''
    copy scan dicom shared network dir to destinationdir
    '''
    try:
        logger.debug(f"Starting DICOM copy process from {sourcedir} to {destinationdir}")
        
        for dir in os.listdir(sourcedir):
            dicom_dir = os.path.join(sourcedir, dir)
            logger.debug(f"Processing directory: {dicom_dir}")
            
            if os.path.isdir(dicom_dir):
                try:
                    dir_size = os.path.getsize(dicom_dir)
                    logger.debug(f"Directory size: {dir_size}")
                    
                    created_date = timezone.make_aware(
                        datetime.fromtimestamp(os.path.getctime(dicom_dir)),
                        timezone=timezone.get_current_timezone()
                    )
                    logger.debug(f"Directory creation date: {created_date}")
                    
                    modified_date = timezone.make_aware(
                        datetime.fromtimestamp(os.path.getmtime(dicom_dir)),
                        timezone=timezone.get_current_timezone()
                    )
                    logger.debug(f"Directory modification date: {modified_date}")

                    if modified_date.date() == datetime.today().date():
                        destination_dir = os.path.join(destinationdir, dir)
                        existing_dir = CopyDicom.objects.filter(
                            sourcedirname=dicom_dir,
                            dirmodifieddate=modified_date
                        )

                        if not existing_dir:
                            try:
                                shutil.copytree(
                                    dicom_dir,
                                    destination_dir
                                )
                                CopyDicom(
                                    sourcedirname=dicom_dir,
                                    destinationdirname=destination_dir,
                                    dircreateddate=created_date,
                                    dirmodifieddate=modified_date,
                                    dirsize=dir_size
                                ).save()
                                logger.info(f"Successfully copied and created new CopyDicom object for {dir}")
                            except Exception as e:
                                logger.error(f"Error copying directory {dir}: {str(e)}")
                        else:
                            logger.info(f"Matching object already exists for {dir}")
                except Exception as e:
                    logger.error(f"Error processing directory {dir}: {str(e)}")
                    
        logger.info("DICOM copy process completed successfully")
        return True

    except Exception as e:
        logger.error(f"Unexpected error in copydicom function: {str(e)}")
        return False
