from dicomapp.models import *
from logging import getLogger
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
logger = getLogger(__name__)

def copy_dicom(datastore_path, target_path = None, task_id=None) -> dict:
    """
    This task will copy folders from the datastore path to the target path. 
    1. It will go through each folder in the datastore path.
    2. It will get the folder path and store it in the field called source_directory.
    3. It will get the creation date and modification date of the directory and store these in the fields called source_directory_creation_date and source_directory_modification_date.
    4. It will calculate the size of the directory and store it in the field called source_directory_size.
    5. It will copy the directory to the target path if the following conditions are met:
        a. The directory has been modified since the past 1 week 
        b. The directory has been modified not less than the past 10 minutes from the current time
        c. The directory's modification time is different from what's stored in the database

    6. It will save the task_id of the celery task in the field called task_id.
    It will run as a part of the celery task. 
    As it will be triggering a task so the return statement for the next task will include a dictionary with the status, task_id and the list of target paths which will be directory paths of the folders created inside the target directory.  

    Args:
        datastore_path (str): The path to the datastore directory.
        target_path (str): The path to the target directory. If not provided, the default path will be used.
        task_id (str): The id of the celery task.

    Returns:
        dict: A dictionary containing:
            - status: The status of the operation ('success', 'partial_failure', or 'failure')
            - task_id: The id of the celery task
            - target_paths: List of paths where DICOM directories were copied
            - error: Error message (only present if status is 'failure')
    """

    logger.info(f"Starting DICOM copy process from {datastore_path} to {target_path}")
    
    try:
        # Convert paths to strings if they're Path objects
        datastore_path = str(datastore_path)
        if target_path is not None:
            target_path = str(target_path)
        
        if target_path is None:
            target_folder_string = f"folders/folder_for_dicom_import/"
            target_path = os.path.join(settings.BASE_DIR, target_folder_string)
        
        # Ensure target directory exists
        os.makedirs(target_path, exist_ok=True)
        
        result = {
            'status': 'success',
            'task_id': task_id,
            'target_paths': [],
            'copy_dicom_task_id': []
        }
        
        current_time = timezone.now()
        # get the date time to start pulling data from the datastore
        dicom_path_config = DicomPathConfig.objects.first()
        if dicom_path_config and dicom_path_config.date_time_to_start_pulling_data:
            date_time_to_start_pulling_data = dicom_path_config.date_time_to_start_pulling_data
            logger.info(f"Date time to start pulling data from the datastore: {date_time_to_start_pulling_data}")
        else:
            date_time_to_start_pulling_data = current_time
            logger.warning("No valid date time to start pulling data from the datastore found, using current time")

        # Get the time delta w.r.t to date_time_to_start_pulling_data
        pull_start_time = date_time_to_start_pulling_data - timedelta(minutes=10)
        logger.info(f"Pull start time: {pull_start_time}")
        ten_minutes_ago = current_time - timedelta(minutes=10)
        logger.info(f"Ten minutes ago: {ten_minutes_ago}")
        # Validate time window
        if pull_start_time > current_time:
            logger.warning(f"Pull start time {pull_start_time} is in the future, adjusting to current time")
            pull_start_time = current_time - timedelta(minutes=20)
            logger.info(f"Pull start time: {pull_start_time}")
        # Iterate through directories in datastore_path
        for item in os.listdir(datastore_path):
            source_dir = os.path.join(datastore_path, item)
            
            # Skip if not a directory
            if not os.path.isdir(source_dir):
                logger.debug(f"Skipping {item} as it's not a directory")
                continue
                
            # Get directory stats
            stats = os.stat(source_dir)
            creation_time = datetime.fromtimestamp(stats.st_ctime)
            modification_time = datetime.fromtimestamp(stats.st_mtime)
            
            # Calculate directory size
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(source_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            
            logger.info(f"Directory {item}: Size={total_size}, Modified={modification_time}")
            
            # Check if directory exists in database and compare modification times
            try:
                existing_entry = CopyDicomTaskModel.objects.get(source_directory=source_dir)
                # check if the copy_completed field is True. If so skip the directory.
                if existing_entry.copy_completed:
                    logger.debug(f"Skipping {item} as it has been already copied")
                    continue
                else:
                    db_modification_time = existing_entry.source_directory_modification_date
                    
                # Skip if modification time hasn't changed
                if db_modification_time and db_modification_time == modification_time:
                    logger.debug(f"Skipping {item} as modification time hasn't changed")
                    continue
            except CopyDicomTaskModel.DoesNotExist:
                # Directory not in database, will be processed
                pass
            
            # Check modification time conditions
            if (modification_time >= pull_start_time and 
                modification_time < ten_minutes_ago):
                
                # Create target directory
                target_dir = os.path.join(target_path, item)
                
                try:
                    # Store directory information in database
                    dicom_dir, created = CopyDicomTaskModel.objects.update_or_create(
                        source_directory = source_dir,
                        defaults={
                            'source_directory_creation_date': creation_time,
                            'source_directory_modification_date': modification_time,
                            'source_directory_size': total_size,
                            'target_directory': target_dir,
                            'task_id': task_id,
                            'copy_completed': True
                        }
                    )
                    logger.info(f"Created/Updated database entry for {item}")

                    # Always copy the directory to the target directory so that even if modifications are made the copy function copies the source directory.
                    shutil.copytree(source_dir, target_dir)
                    result['target_paths'].append(target_dir)  # Already a string
                    result['copy_dicom_task_id'].append(str(dicom_dir.id))  # Convert UUID to string
                    logger.info(f"Successfully copied {item} to {target_dir}")                    
                    
                except Exception as e:
                    logger.error(f"Error copying directory {item}: {str(e)}")
                    result['status'] = 'partial_failure'
            else:
                logger.debug(f"Skipping {item} due to modification time constraints")
        
        logger.info(f"DICOM copy process completed with status {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to complete DICOM copy process: {str(e)}")
        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e)
        }






