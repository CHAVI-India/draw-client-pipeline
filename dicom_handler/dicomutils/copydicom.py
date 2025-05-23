# # copydicom.py

# import os
# import shutil
# from datetime import datetime, timezone
# from dicom_handler.models import CopyDicom, ProcessingStatusChoices
# from django.utils import timezone
# import logging


# # Get logger
# logger = logging.getLogger('dicom_handler_logs')

# def copydicom(sourcedir, destinationdir):
#     '''
#     Copy DICOM directories from a source location to a destination location with intelligent handling.
    
#     This function copies DICOM directories from a source network location to a local destination,
#     while implementing several intelligent features:
    
#     1. Only processes directories modified on the current date
#     2. Maintains a database record of all copied directories
#     3. Avoids duplicate copying of unchanged directories
#     4. Detects and updates directories that have been modified since last copy
#     5. Tracks copy status in the database for downstream processing
    
#     The function handles several scenarios:
#     - If a directory doesn't exist at the destination, it's copied and recorded
#     - If a directory exists at the destination but has no database record, a record is created
#     - If a directory exists at the destination with a database record and the source is newer,
#       the destination is updated with the latest content from the source
#     - If a directory exists with the exact same modification date, it's skipped entirely
    
#     Parameters:
#     -----------
#     sourcedir : str
#         The source directory path containing DICOM folders to be copied.
#         This is typically a network share or remote location.
    
#     destinationdir : str
#         The destination directory path where DICOM folders will be copied to.
#         This is typically a local path for further processing.
    
#     Returns:
#     --------
#     dict
#         A dictionary containing:
#         - status: 'success' or 'failure'
#         - message: A descriptive message about the operation
#         - copied_directories: List of successfully copied directory paths
#         - failed_directories: List of directories that failed to copy
#     '''
#     try:
#         logger.debug(f"Starting DICOM copy process from {sourcedir} to {destinationdir}")
        
#         # Convert input paths to strings if they aren't already
#         sourcedir = str(sourcedir)
#         destinationdir = str(destinationdir)
        
#         # Track results
#         copied_directories = []
#         failed_directories = []
        
#         for dir in os.listdir(sourcedir):
#             dicom_dir = os.path.join(sourcedir, dir)
#             logger.debug(f"Processing directory: {dicom_dir}")
            
#             if os.path.isdir(dicom_dir):
#                 try:
#                     dir_size = os.path.getsize(dicom_dir)
#                     logger.debug(f"Directory size: {dir_size}")
                    
#                     created_date = timezone.make_aware(
#                         datetime.fromtimestamp(os.path.getctime(dicom_dir)),
#                         timezone=timezone.get_current_timezone()
#                     )
#                     logger.debug(f"Directory creation date: {created_date}")
                    
#                     modified_date = timezone.make_aware(
#                         datetime.fromtimestamp(os.path.getmtime(dicom_dir)),
#                         timezone=timezone.get_current_timezone()
#                     )
#                     logger.debug(f"Directory modification date: {modified_date}")
#                     today = datetime.today().date()
#                     days_difference = (today - modified_date.date()).days

#                     logger.debug(f"Days difference: {days_difference}")

#                     if days_difference <= 7 and days_difference >= 0:
#                         # Ensure destination_dir is a string
#                         destination_dir = str(os.path.join(destinationdir, dir))
#                         existing_dir = CopyDicom.objects.filter(
#                             sourcedirname=dicom_dir,
#                             dirmodifieddate=modified_date
#                         )
#                         logger.debug(f"days difference: {days_difference}")
#                         if not existing_dir:
#                             # Check if destination directory already exists physically
#                             if os.path.exists(destination_dir):
#                                 logger.info(f"Destination directory already exists for {dir}, checking modification date")
#                                 # Get existing entry or create new one
#                                 copy_dicom_obj, created = CopyDicom.objects.get_or_create(
#                                     destinationdirname=destination_dir,
#                                     defaults={
#                                         'sourcedirname': dicom_dir,
#                                         'dircreateddate': created_date,
#                                         'dirmodifieddate': modified_date,
#                                         'dirsize': dir_size,
#                                         'processing_status': ProcessingStatusChoices.COPIED.value
#                                     }
#                                 )
                                
#                                 if created:
#                                     logger.info(f"Created tracking record for existing directory {dir}")
#                                 else:
#                                     # Check if the directory has been modified since last recorded
#                                     if copy_dicom_obj.dirmodifieddate and modified_date > copy_dicom_obj.dirmodifieddate:
#                                         logger.info(f"Directory {dir} has newer modifications, copying new files")
                                        
#                                         try:
#                                             # Remove the old directory first to ensure clean copy
#                                             shutil.rmtree(destination_dir)
                                            
#                                             # Copy the updated directory
#                                             shutil.copytree(dicom_dir, destination_dir)
                                            
#                                             # Update the database record
#                                             copy_dicom_obj.dirmodifieddate = modified_date
#                                             copy_dicom_obj.dirsize = dir_size
#                                             copy_dicom_obj.processing_status = ProcessingStatusChoices.COPIED.value
#                                             copy_dicom_obj.save()
                                            
#                                             logger.info(f"Updated directory {dir} with new files and updated database record")
#                                             copied_directories.append(destination_dir)
#                                         except Exception as e:
#                                             logger.error(f"Failed to update directory {dir}: {str(e)}")
#                                             failed_directories.append(destination_dir)
#                                     else:
#                                         logger.info(f"Tracking record already exists for {dir} and no newer modifications found")
#                             else:
#                                 try:
#                                     shutil.copytree(
#                                         dicom_dir,
#                                         destination_dir
#                                     )
#                                     CopyDicom(
#                                         sourcedirname=dicom_dir,
#                                         destinationdirname=destination_dir,
#                                         dircreateddate=created_date,
#                                         dirmodifieddate=modified_date,
#                                         dirsize=dir_size,
#                                         processing_status=ProcessingStatusChoices.COPIED.value
#                                     ).save()
#                                     logger.info(f"Successfully copied and created new CopyDicom object for {dir}")
#                                     copied_directories.append(destination_dir)
#                                 except Exception as e:
#                                     logger.error(f"Error copying directory {dir}: {str(e)}")
#                                     failed_directories.append(destination_dir)
#                         else:
#                             logger.info(f"Matching object already exists for {dir}")
#                 except Exception as e:
#                     logger.error(f"Error processing directory {dir}: {str(e)}")
#                     failed_directories.append(dicom_dir)
                    
#         logger.info("DICOM copy process completed successfully")
        
#         # Return detailed results
#         return {
#             "status": "success" if not failed_directories else "partial_failure",
#             "message": f"Successfully copied {len(copied_directories)} directories, {len(failed_directories)} failed" if failed_directories else "Successfully copied all directories",
#             "copied_directories": copied_directories,
#             "failed_directories": failed_directories
#         }

#     except Exception as e:
#         logger.error(f"Unexpected error in copydicom function: {str(e)}")
#         return {
#             "status": "failure",
#             "message": f"Unexpected error: {str(e)}",
#             "copied_directories": [],
#             "failed_directories": []
#         }
