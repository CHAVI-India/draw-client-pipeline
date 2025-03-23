from dicom_handler.models import DicomPathConfig, CopyDicom, ProcessingStatusChoices
import os
import zipfile
import datetime
from django.utils import timezone
import logging
from django.conf import settings
# Get logger
logger = logging.getLogger('dicom_handler_logs')

def send_to_autosegmentation(modeladmin, request, queryset):
    '''
    This admin action will take an uploaded zip folder and send it to the import DICOM directory for further processsing. 
    The action will extract the contents of the zip file into a directory inside the import_dicom folder path. 
    If there are subfolder inside the zip file it should put each of these subfolders into a seperate directory inside the import_dicom folder. 
    For example if the zip file has the strcuture Folder A/Folder B/Folder C/DICOM file1.dcm then the DICOM file1.dcm will be extracted into a directory called Folder C inside the import_dicom folder.
    The action will also create a new entry in the CopyDicom model with the status as COPIED.
    '''
    # Check if any files are selected
    if not queryset.exists():
        return "No files selected for processing."
    
    results = []
    
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
            
            # Extract the contents of the zip file
            with zipfile.ZipFile(obj.dicom_file.path, 'r') as zip_ref:
                # Get list of all files in the zip
                file_list = zip_ref.namelist()
                
                # Process each file in the zip
                for file_path in file_list:
                    # Skip directories (we'll create them as needed)
                    if file_path.endswith('/'):
                        continue
                    
                    # Get the deepest subfolder name
                    path_parts = file_path.split('/')
                    if len(path_parts) > 1:
                        deepest_folder = path_parts[-2]
                        target_dir = os.path.join(import_dir, deepest_folder)
                    else:
                        # If no subfolder, use the filename as directory
                        target_dir = os.path.join(import_dir, os.path.splitext(path_parts[0])[0])
                    
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
    
    # Display the message in Django admin
    modeladmin.message_user(request, final_message)

# Make the admin action have a nice display name
send_to_autosegmentation.short_description = "Send selected DICOM zip files to autosegmentation"


