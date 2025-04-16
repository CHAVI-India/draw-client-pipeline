from dicomapp.models import *
from logging import getLogger
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
logger = getLogger(__name__)

# Function to find all directories containing files directly (not counting files in subdirectories)
def find_directories_with_direct_files(base_path):

    # Use Pathlib to list of all files and folders in the base path
    path_object = Path(base_path)
    # Get all files and folders in the base path
    items = path_object.glob('*')
    # Sort the items by modification time
    sorted_items = sorted(items, key=lambda item: item.stat().st_mtime)
    # Only keep the sorted items which are modified after the pull start time
    sorted_items = [item for item in sorted_items if item.stat().st_mtime >= pull_start_time]
    # Return the directory within the sorted_items only.
    all_dirs = [str(item) for item in sorted_items if item.is_dir()]
    logger.info(f"Found {len(all_dirs)} total directories")

    #dirs_with_files = []
    # First get all directories using os.walk()
    #all_dirs = []
    #for root, dirs, _ in os.walk(base_path):
        # Skip the base directory itself
        # if root == base_path:
        #     continue
        # all_dirs.append(root)
    
    dirs_with_files = []
    # Then check each directory to see if it contains files directly
    for dir_path in all_dirs:
        has_files = False
        files_count = 0
        # Check for files directly in this directory (not in subdirectories)
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            if os.path.isfile(item_path):
                has_files = True
                files_count += 1
        
        if has_files:
            dirs_with_files.append(dir_path)
            logger.info(f"Directory {dir_path} has {files_count} files directly")
        else:
            logger.debug(f"Directory {dir_path} has no direct files, skipping")
    
    logger.info(f"Found {len(dirs_with_files)} directories with direct files")
    return dirs_with_files


def copy_dicom(datastore_path, target_path = None, task_id=None) -> dict:
    """
    This task will recursively scan folders from the datastore path and copy all directories containing files to the target path. 
    1. It will recursively find all directories containing files in the datastore path.
    2. For each directory containing files, it will:
       a. Get the full path and store it in the field called source_directory.
       b. Get the creation date and modification date and store these in the fields.
       c. Calculate the size of the directory and store it.
    3. It will copy the directory to the target path if the following conditions are met:
        a. The directory has been modified since the past 1 week 
        b. The directory has been modified not less than the past 10 minutes from the current time
        c. The directory's modification time is different from what's stored in the database

    4. It will save the task_id of the celery task in the field called task_id.
    It will run as a part of the celery task. 

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
            logger.info(f"Date time to start pulling data from the datastore: {date_time_to_start_pulling_data} (timezone: {date_time_to_start_pulling_data.tzinfo})")
        else:
            date_time_to_start_pulling_data = current_time
            logger.warning("No valid date time to start pulling data from the datastore found, using current time")

        # Get the time delta w.r.t to date_time_to_start_pulling_data
        pull_start_time = date_time_to_start_pulling_data - timedelta(minutes=10)
        logger.info(f"Pull start time: {pull_start_time} (timezone: {pull_start_time.tzinfo})")
        ten_minutes_ago = current_time - timedelta(minutes=10)
        logger.info(f"Ten minutes ago: {ten_minutes_ago} (timezone: {ten_minutes_ago.tzinfo})")
        
        # Validate time window
        if pull_start_time > current_time:
            logger.warning(f"Pull start time {pull_start_time} is in the future, adjusting to current time")
            pull_start_time = current_time - timedelta(minutes=20)
            logger.info(f"Pull start time: {pull_start_time} (timezone: {pull_start_time.tzinfo})")
        
        logger.info(f"Starting directory scan in {datastore_path}")
        
        # Find all directories with direct files
        directories_with_files = find_directories_with_direct_files(datastore_path)
        
        if not directories_with_files:
            logger.warning(f"No directories with files found in {datastore_path}")
            return {
                'status': 'success',
                'task_id': task_id,
                'target_paths': [],
                'copy_dicom_task_id': [],
                'message': 'No directories with files found'
            }
            
        logger.info(f"Processing {len(directories_with_files)} directories")
        
        # Process each directory containing files
        for source_dir in directories_with_files:
            # Extract directory name for the target path (use the last part of the path)
            dir_name = os.path.basename(source_dir)
            
            # Get directory stats
            stats = os.stat(source_dir)
            # Convert timestamps to timezone-aware datetimes
            creation_time = timezone.make_aware(datetime.fromtimestamp(stats.st_ctime))
            modification_time = timezone.make_aware(datetime.fromtimestamp(stats.st_mtime))
            logger.info(f"Directory {source_dir} modification time: {modification_time} (timezone: {modification_time.tzinfo})")
            
            
            # Check if directory exists in database and compare modification times
            try:
                existing_entry = CopyDicomTaskModel.objects.get(source_directory=source_dir)
                # check if the copy_completed field is True. If so skip the directory.
                if existing_entry.copy_completed:
                    logger.debug(f"Skipping {source_dir} as it has been already copied")
                    continue
                else:
                    db_modification_time = existing_entry.source_directory_modification_date
                    
                # Skip if modification time hasn't changed
                if db_modification_time and db_modification_time == modification_time:
                    logger.debug(f"Skipping {source_dir} as modification time hasn't changed")
                    continue
            except CopyDicomTaskModel.DoesNotExist:
                # Directory not in database, will be processed
                pass
            
            # Check modification time conditions
            if (modification_time >= pull_start_time and 
                modification_time < ten_minutes_ago):
                
                # Calculate size of only the files directly in this directory (not in subdirectories)
                total_size = 0
                for f in os.listdir(source_dir):
                    file_path = os.path.join(source_dir, f)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
                
                logger.info(f"Directory {source_dir}: Size={total_size}, Modified={modification_time}")

                # Create target directory with same name as source
                target_dir = os.path.join(target_path, dir_name)
                
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
                    logger.info(f"Created/Updated database entry for {source_dir}")

                    # Create target directory if it doesn't exist
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Copy only the files directly in this directory (not subdirectories)
                    files_copied = 0
                    for item in os.listdir(source_dir):
                        source_item = os.path.join(source_dir, item)
                        # Only copy files, not subdirectories
                        if os.path.isfile(source_item):
                            target_file = os.path.join(target_dir, item)
                            shutil.copy2(source_item, target_file)
                            files_copied += 1
                    
                    result['target_paths'].append(target_dir)  # Already a string
                    result['copy_dicom_task_id'].append(str(dicom_dir.id))  # Convert UUID to string
                    logger.info(f"Successfully copied {files_copied} files from {source_dir} to {target_dir}")
                    
                except Exception as e:
                    logger.error(f"Error copying directory {source_dir}: {str(e)}")
                    result['status'] = 'partial_failure'
            else:
                logger.debug(f"Skipping {source_dir} due to modification time constraints")
        
        logger.info(f"DICOM copy process completed with status {result}")

        # Update the dicom_path_config with the current time
        dicom_path_config.date_time_to_start_pulling_data = timezone.now()
        dicom_path_config.save()
        return result
        
    except Exception as e:
        logger.error(f"Failed to complete DICOM copy process: {str(e)}")
        return {
            'status': 'failure',
            'task_id': task_id,
            'error': str(e)
        }






