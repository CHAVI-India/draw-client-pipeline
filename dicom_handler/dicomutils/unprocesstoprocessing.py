import shutil
import os
import glob
import logging
from dicom_handler.models import DicomPathConfig
from django.conf import settings

# Get logger
logger = logging.getLogger('dicom_handler_logs')

def check_and_delete_yaml(folder_path):
    """
    Check for YAML files in a given folder and delete them
    
    Args:
        folder_path (str): Path to the folder to check
        
    Returns:
        None
    """
    logger.info(f"Starting YAML file check and delete in folder: {folder_path}")
    
    try:
        yaml_files = glob.glob(os.path.join(folder_path, "*.yml"))
        logger.debug(f"Found {len(yaml_files)} YAML files")
        
        for yaml_file in yaml_files:
            try:
                logger.debug(f"Attempting to delete YAML file: {yaml_file}")
                os.remove(yaml_file)
                logger.info(f"Successfully deleted YAML file: {yaml_file}")
            except OSError as e:
                logger.error(f"Error deleting YAML file {yaml_file}: {str(e)}")
                raise
        
        logger.info("YAML file check and delete operation completed")
    
    except Exception as e:
        logger.error(f"Error in check_and_delete_yaml function: {str(e)}")
        raise

def move_folder_with_yaml_check(unprocess_dir, copy_yaml):
    """
    Move a folder to the processing directory after YAML operations
    
    Args:
        unprocess_dir (str): Path to the unprocessed directory
        copy_yaml (str): Path to the YAML file to copy
        
    Returns:
        None
    """
    logger.info("Starting folder move operation with YAML check")
    
    try:
        # Get the path to the dicom_processing_folder
        processing_dir = os.path.join(settings.BASE_DIR, 'dicom_processing_folder')
        if not os.path.exists(processing_dir):
            os.makedirs(processing_dir)
            
        logger.debug(f"Processing directory path: {processing_dir}")
        
        # Check and delete existing YAML files
        logger.info(f"Checking for existing YAML files in: {unprocess_dir}")
        check_and_delete_yaml(folder_path=unprocess_dir)
        
        # Copy new YAML file
        try:
            logger.debug(f"Copying YAML file from {copy_yaml} to {unprocess_dir}")
            shutil.copy2(copy_yaml, unprocess_dir)
            logger.info("Successfully copied new YAML file")
        except Exception as e:
            logger.error(f"Error copying YAML file: {str(e)}")
            raise
        
        # Move directory
        try:
            logger.debug(f"Moving directory from {unprocess_dir} to {processing_dir}")
            shutil.move(unprocess_dir, processing_dir)
            logger.info("Successfully moved directory to processing folder")
        except Exception as e:
            logger.error(f"Error moving directory: {str(e)}")
            raise
        
        logger.info("Folder move operation with YAML check completed successfully")
    
    except Exception as e:
        logger.error(f"Error in move_folder_with_yaml_check function: {str(e)}")
        raise
