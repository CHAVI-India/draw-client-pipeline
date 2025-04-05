# import os
# import shutil
# import logging
# from django.conf import settings
# from dicom_handler.models import DicomUnprocessed, ModelYamlInfo, ProcessingStatus
# from django.contrib import admin
# from django.contrib import messages
# from dicom_handler.tasks import read_dicom_metadata_task

# logger = logging.getLogger(__name__)

# def move_from_unprocessed_to_processing(modeladmin, request, queryset):
#     '''
#     This function will move the dicom series in the unprocessed folder to the processing folder.
#     It will also trigger the read_dicom_metadata_task to extract the metadata and send it to the deidentification process.

#     The way it will work is this.
#     1. First it will check if a YAML file exists inside the series folder. (field series_folder_location inside the DicomUnprocessed model)
#     2. If it does it will delete the YAML file.
#     3. It will then copy the YAML file selected by the user into the series folder.
#     4. The YAML file chosen will be based on the file selected by the user in the DicomUnprocessed model which is a FK reference to the ModelYamlInfo model.
#     5. The name of the field in the DicomUnprocessed model is yaml_attached. The path to the YAML file is stored in the ModelYamlInfo model in the field called yaml_path.
#     6. The function will then move the series folder to the processing folder. (located at folder_for_dicom_processing)
#     7. It will update the DicomUnprocessed model to set the unprocessed field to False. Additionally it will set the series_folder_location field to the path of the folder in the processing folder.
#     7. The function will then trigger the read_dicom_metadata_task to extract the metadata and send it to the deidentification process. The read_dicom_metadata_task will be called with the following parameters:
#         - series_folder_location - this is new location of the series folder in the processing folder.


        


#     This custom admin action will be triggered on the admin page for the DicomUnprocessed model.
#     '''
#     # Path to processing folder
#     base_dir = settings.BASE_DIR
#     processing_folder = os.path.join(base_dir, 'folder_dicom_processing')
#     unprocessed_folder = os.path.join(base_dir, 'folder_unprocessed_dicom')
#     deidentified_folder = os.path.join(base_dir, 'folder_for_deidentification')
    
#     # Ensure processing folder exists
#     os.makedirs(processing_folder, exist_ok=True)
    
#     processed_count = 0
#     error_count = 0
#     skipped_count = 0
#     processed_patients = []
#     failed_patients = []
    
#     # Check if any records match our criteria
#     filtered_queryset = queryset.filter(unprocessed=True, yaml_attached__isnull=False)
#     if not filtered_queryset.exists():
#         modeladmin.message_user(
#             request, 
#             "No eligible records found. Please select records that are marked as unprocessed and have a YAML file attached.", 
#             level=messages.WARNING
#         )
#         return
    
#     # Use the queryset provided to the admin action
#     for record in filtered_queryset:
#         try:
#             logger.info(f"Processing record {record.id} - {record.patientid}")
            
#             # 1. Check if a YAML file exists in the series folder
#             series_folder = record.series_folder_location
#             if not os.path.exists(series_folder):
#                 logger.error(f"Series folder does not exist: {series_folder}")
#                 skipped_count += 1
#                 failed_patients.append(f"{record.patientid} (folder not found)")
#                 continue
                
#             yaml_files = [f for f in os.listdir(series_folder) if f.endswith('.yaml') or f.endswith('.yml')]
            
#             # 2. Delete existing YAML files if any
#             for yaml_file in yaml_files:
#                 yaml_path = os.path.join(series_folder, yaml_file)
#                 os.remove(yaml_path)
#                 logger.info(f"Removed existing YAML file: {yaml_path}")
            
#             # 3 & 4. Copy the selected YAML file to the series folder
#             yaml_source_path = record.yaml_attached.yaml_path
#             yaml_filename = os.path.basename(yaml_source_path)
#             yaml_destination_path = os.path.join(series_folder, yaml_filename)
            
#             shutil.copy2(yaml_source_path, yaml_destination_path)
#             logger.info(f"Copied YAML file from {yaml_source_path} to {yaml_destination_path}")
            
#             # 6. Move the series folder to the processing folder
#             series_foldername = os.path.basename(series_folder)
#             new_series_folder = os.path.join(processing_folder, series_foldername)
            
#             # Ensure the destination doesn't exist before moving
#             if os.path.exists(new_series_folder):
#                 shutil.rmtree(new_series_folder)
#                 logger.info(f"Removed existing processing folder: {new_series_folder}")
                
#             shutil.move(series_folder, new_series_folder)
#             logger.info(f"Moved series folder from {series_folder} to {new_series_folder}")
            
#             # 7. Update the DicomUnprocessed record
#             record.unprocessed = False
#             record.series_folder_location = new_series_folder
#             record.save()
            
#             # Create a processing status record
#             ProcessingStatus.objects.create(
#                 patient_id=record,
#                 status=f"YAML attached: {record.yaml_attached.yaml_name}",
#                 dicom_move_folder_status="Moved to processing folder",
#                 yaml_attach_status="YAML file attached"
#             )
            
#             # 8. Trigger the read_dicom_metadata_task instead of directly calling the function
#             task = read_dicom_metadata_task.delay(new_series_folder)
#             logger.info(f"Triggered read_dicom_metadata_task with task ID: {task.id} for folder: {new_series_folder}")
            
#             processed_count += 1
#             processed_patients.append(f"{record.patientid}")
#             logger.info(f"Successfully processed record {record.id}")
            
#         except Exception as e:
#             error_count += 1
#             failed_patients.append(f"{record.patientid} ({str(e)[:50]}...)")
#             logger.error(f"Error processing record {record.id}: {str(e)}")
    
#     # Create detailed status message
#     if processed_count > 0:
#         message = f"Successfully processed {processed_count} DICOM series."
#         if len(processed_patients) <= 5:
#             message += f" Patients: {', '.join(processed_patients)}."
#         level = messages.SUCCESS
#     else:
#         message = "No DICOM series were processed successfully."
#         level = messages.ERROR
    
#     if error_count > 0:
#         message += f" Failed to process {error_count} series."
#         if len(failed_patients) <= 5:
#             message += f" Failed patients: {', '.join(failed_patients)}."
#         level = messages.WARNING
    
#     if skipped_count > 0:
#         message += f" Skipped {skipped_count} series due to missing folders."
    
#     modeladmin.message_user(request, message, level=level)

# move_from_unprocessed_to_processing.short_description = "Move selected records for Processing"


