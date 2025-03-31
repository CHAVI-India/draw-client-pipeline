from dicom_handler.models import DicomPathConfig, CopyDicom, ProcessingStatusChoices
import os
import zipfile
import datetime
import random
import string
from django.utils import timezone
import logging
from django.conf import settings
from dicom_handler.tasks import dicom_series_separation_task
# Get logger
logger = logging.getLogger('dicom_handler_logs')

def send_to_autosegmentation(modeladmin, request, queryset):
    '''
    This admin action processes uploaded DICOM zip files and prepares them for autosegmentation.
    
    The function:
    1. Extracts contents of zip files to the import DICOM directory as follows:
       - For zip files with subfolders: Files are extracted into directories named after the deepest subfolder 
         with a random 5-character suffix to ensure uniqueness (e.g., "Series1_a2b3c")
       - For zip files without subfolders: All files are extracted into a single directory named after the zip file
    
    2. Creates a new entry in the CopyDicom model with status COPIED for each target directory.
    
    3. Triggers the dicom_series_separation_task separately for each created directory to process the DICOM files
       and initiate subsequent processing tasks.
    
    Example:
    If a zip file has the structure "Folder A/Folder B/Folder C/file1.dcm", the file will be extracted into
    a directory called "Folder C_xxxxx" (where xxxxx is a random string) inside the import_dicom folder.
    '''
    # Check if any files are selected
    if not queryset.exists():
        return "No files selected for processing."
    
    results = []
    # Keep track of all target directories that were created
    all_target_directories = set()

    for obj in queryset:
        try:
            # Get the path configuration
            path_config = DicomPathConfig.get_instance()
            
            # Create the import directory if it doesn't exist
            import_dir = os.path.join(settings.BASE_DIR, 'folder_for_dicom_import')
            if not os.path.exists(import_dir):
                os.makedirs(import_dir)
            
            # Track processing details for admin message
            processed_folders = set()
            total_files = 0

            # Get the zip filename without extension to use as directory name for Scenario 1
            zip_filename = os.path.splitext(os.path.basename(obj.dicom_file.path))[0]
            
            # Check if this is a "no subfolder" zip file
            has_subfolders = False
            with zipfile.ZipFile(obj.dicom_file.path, 'r') as check_zip:
                for path in check_zip.namelist():
                    if '/' in path and not path.endswith('/'):
                        has_subfolders = True
                        break
            # Generate a random string to ensure unique folder names
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            
            # Extract the contents of the zip file
            with zipfile.ZipFile(obj.dicom_file.path, 'r') as zip_ref:
                # Get list of all files in the zip
                file_list = zip_ref.namelist()
                
                # Process each file in the zip
                for file_path in file_list:
                    # Skip directories (we'll create them as needed)
                    if file_path.endswith('/'):
                        continue
                    
                    # Determine target directory based on whether there are subfolders
                    path_parts = file_path.split('/')
                    if has_subfolders and len(path_parts) > 1:
                        # Original behavior for files in subfolders
                        deepest_folder = path_parts[-2]
                        target_dir = os.path.join(import_dir, f"{deepest_folder}_{random_suffix}")
                    else:
                        # New behavior for Scenario 1: All files go to a single directory named after the zip file
                        target_dir = os.path.join(import_dir, zip_filename)
                    
                    # Add this target directory to our set of all directories
                    all_target_directories.add(target_dir)

                    # Create the target directory if it doesn't exist
                    if not os.path.exists(target_dir):
                        os.makedirs(target_dir)
                    
                    # Extract the file to the target directory
                    file_data = zip_ref.read(file_path)
                    with open(os.path.join(target_dir, os.path.basename(file_path)), 'wb') as f:
                        f.write(file_data)
                    
                    # Update statistics
                    total_files += 1
                    processed_folders.add(target_dir)
                    
                    # Get current time using Django's timezone-aware datetime
                    current_time = timezone.now()
                    
                    # Get directory size
                    dir_size = 0
                    for dirpath, dirnames, filenames in os.walk(target_dir):
                        for f in filenames:
                            fp = os.path.join(dirpath, f)
                            dir_size += os.path.getsize(fp)
                    
                    # Find or create a CopyDicom record and ensure processing_status is COPIED
                    copy_dicom_obj, created = CopyDicom.objects.get_or_create(
                        destinationdirname=target_dir,
                        defaults={
                            'sourcedirname': obj.dicom_file.path,
                            'dircreateddate': current_time,
                            'dirmodifieddate': current_time,
                            'dirsize': dir_size,
                            'processing_status': ProcessingStatusChoices.COPIED
                        }
                    )
                    
                    # If the record already existed, update its processing_status to COPIED
                    if not created:
                        copy_dicom_obj.processing_status = ProcessingStatusChoices.COPIED
                        copy_dicom_obj.save(update_fields=['processing_status'])
                        logger.info(f"Updated processing status to COPIED for existing record: {target_dir}")
                    else:
                        logger.info(f"Successfully extracted and created CopyDicom record for {target_dir}")
            
            # Mark the uploaded file as processed
            obj.send_to_autosegmentation = True
            obj.save()
            
            # Generate file summary for this file
            total_folders = len(processed_folders)
            folder_list = "\n- ".join([""] + [os.path.basename(folder) for folder in processed_folders])
            
            file_result = (
                f"File: {os.path.basename(obj.dicom_file.path)}\n"
                f"Files extracted: {total_files}\n"
                f"Folders created: {total_folders}{folder_list}"
            )
            
            results.append(file_result)
            
        except Exception as e:
            error_message = f"Error processing {os.path.basename(obj.dicom_file.path)}: {str(e)}"
            logger.error(error_message)
            results.append(error_message)
    
    # Create the final message for Django admin
    final_message = "\n\n".join(results)
    final_message += f"\n\nAll files were extracted to: {import_dir}"
    
    # Trigger the dicom series separation task for each target directory
    triggered_tasks = 0
    for target_dir in all_target_directories:
        logger.info(f"Triggering dicom_series_separation_task for directory: {target_dir}")
        dicom_series_separation_task.delay(target_dir)
        triggered_tasks += 1
    
    final_message += f"\n\nTriggered DICOM series separation task for {triggered_tasks} directories."
    
    # Display the message in Django admin
    modeladmin.message_user(request, final_message)

# Make the admin action have a nice display name
send_to_autosegmentation.short_description = "Send selected DICOM zip files to autosegmentation"