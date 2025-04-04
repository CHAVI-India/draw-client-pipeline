from django.contrib import messages
from django.utils.text import slugify
import os
import zipfile
import random
import string
from pathlib import Path
from dicom_handler.models import DicomPathConfig

def upload_dicom_zip(modeladmin, request, queryset):
    '''
    This function will be used as an admin action to the DicomFileUpload model
    It will take the zip files selected in the admin page.
    It will extract the contents of the zip file into the datastore path defined by the DicomPathConfig model
    After the extraction is completed it will mark the instance of the DicomFileUpload model as unzipped
    The zip file has to be extracted inside a subfolder named after the zip file without the .zip extension and ensureing the path name is safe.
    '''
    # Get the datastore path from DicomPathConfig
    datastore_path = DicomPathConfig.get_instance().get_safe_path()
    
    if not datastore_path:
        messages.error(request, "Datastore path is not configured. Please configure it first.")
        return
    
    for upload in queryset:
        try:
            # Get the zip file path
            zip_path = upload.file.path
            
            # Create a safe folder name from the zip filename
            zip_name = os.path.splitext(upload.file_name)[0]  # Remove .zip extension
            safe_folder_name = slugify(zip_name)
            
            # Limit to 10 characters and add random string
            safe_folder_name = safe_folder_name[:10]  # Take first 10 characters
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            safe_folder_name = f"{safe_folder_name}_{random_string}"
            
            # Create the target directory
            target_dir = datastore_path / safe_folder_name
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
            
            # Mark as unzipped
            upload.unzipped = True
            upload.save()
            
            messages.success(request, f"Successfully extracted {upload.file_name} to {str(target_dir)}")
            
        except Exception as e:
            messages.error(request, f"Error processing {upload.file_name}: {str(e)}")

# Set the display name for the admin action
upload_dicom_zip.short_description = "Extract selected DICOM zip files to subfolders in the datastore"
