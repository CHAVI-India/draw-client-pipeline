# import random
# import string
# from django.core.management.base import BaseCommand
# import pydicom
# import os
# import pandas as pd
# from deidapp.models import DicomSeries, DicomStudy, Patient, DicomInstance, RTStructFile
# from datetime import date
# import uuid

# class Command(BaseCommand):
#     help = 'Reidentify RT Structure Set DICOM files'

#     def get_referenced_series_uid(self, ds, elem):
#         if elem.tag == (0x0020, 0x000E):
#             print(f"Found Referenced Series Instance UID: {elem.value}")
#             self.found_series_instance_uid = elem.value  # Store the value as an instance variable
        
#     def add_arguments(self, parser):
#         parser.add_argument('source_dir', type=str, help='Source directory containing RTSTRUCT files')
#         parser.add_argument('target_dir', type=str, help='Target directory for processed files')

#     def frame_of_reference_callback(self, ds, elem):
#         """Replace Frame of Reference UIDs"""
#         if elem.tag in [(0x0020,0x0052), (0x3006,0x0024)]:
#             elem.value = self.series.frame_of_reference_uid

#     def sop_instance_callback(self, ds, elem):
#         """Replace Referenced SOP Instance UIDs"""
#         if elem.tag == (0x0008,0x1155):  # Referenced SOP Instance UID
#             deidentified_id = elem.value
#             matching_row = self.df[self.df['deidentified_id'] == deidentified_id]
#             if not matching_row.empty:
#                 elem.value = matching_row.iloc[0]['original_id']
#                 self.replacement_count += 1


#     def handle(self, *args, **options):
#         source_dir = options['source_dir']
#         target_dir = options['target_dir']
        
#         # Create target directory if it doesn't exist
#         os.makedirs(target_dir, exist_ok=True)

#         # Walk through directory and subdirectories
#         for root, dirs, files in os.walk(source_dir):
#             for filename in files:
#                 file_path = os.path.join(root, filename)
#                 print(f"Processing file: {file_path}")  # Debug line
                
#                 try:
#                     # Step 1: Check if file is valid DICOM
#                     try:
#                         ds = pydicom.dcmread(file_path)
#                     except:
#                         print(f"Invalid DICOM file: {file_path}")
#                         continue

#                     # Step 2: Check if modality is RTSTRUCT
#                     if not hasattr(ds, 'Modality') or ds.Modality != 'RTSTRUCT':
#                         print(f"Not a RTSTRUCT file: {file_path}")
#                         continue

#                     # Step 3: Get Referenced Series Instance UID
#                     self.found_series_instance_uid = None  # Initialize before walking
#                     ds.walk(self.get_referenced_series_uid)  # Walk through the dataset

#                     deidentified_series_instance_uid = self.found_series_instance_uid  # Use the stored value

#                     if deidentified_series_instance_uid is None:
#                         print(f"Could not find Referenced Series Instance UID in: {file_path}")
#                         continue

#                     print(deidentified_series_instance_uid)

#                     # Get all series with matching series instance UID
#                     matching_series = DicomSeries.objects.filter(
#                         deidentified_series_instance_uid=deidentified_series_instance_uid
#                     )

#                     if not matching_series.exists():
#                         print(f"No matching DICOM Series Found: {file_path}")
#                         continue

#                     # Log the number of matching series found
#                     print(f"Found {matching_series.count()} series with matching Series Instance UID")
                    
#                     self.series = matching_series.first()

#                     print(f"Selected series with UID: {self.series.series_instance_uid}")

#                     # Step 4 & 5: Get required values from DicomStudy and Patient models
#                     study = self.series.study
#                     patient = study.patient

#                     # Step 5: Replace basic DICOM tags with original values
#                     ds.StudyInstanceUID = study.study_instance_uid
#                     ds.PatientID = patient.patient_id
#                     ds.PatientName = patient.patient_name
#                     ds.StudyDescription = study.study_description
#                     ds.PatientBirthDate = patient.patient_birth_date.strftime('%Y%m%d')
#                     ds.ReferringPhysicianName = "DRAW"
#                     ds.AccessionNumber = "202514789"                    


#                     # Add additional DICOM tag values which will be default for the RTSTRUCT file

#                     # Step 6: Create dataframe of all UIDs
#                     instances = DicomInstance.objects.filter(series=self.series)
#                     series = self.series  # The current series we're working with
#                     study = series.study  # Get the related study through the foreign key
                    
#                     # Collect all UIDs (instance, series, and study level)
#                     df_data = {
#                         'original_id': (
#                             # Instance level UIDs
#                             [inst.sop_instance_uid for inst in instances] +
#                             # Series level UIDs
#                             [series.series_instance_uid] +
#                             # Study level UIDs
#                             [study.study_instance_uid]
#                         ),
#                         'deidentified_id': (
#                             # Instance level UIDs
#                             [inst.deidentified_sop_instance_uid for inst in instances] +
#                             # Series level UIDs
#                             [series.deidentified_series_instance_uid] +
#                             # Study level UIDs
#                             [study.deidentified_study_instance_uid]
#                         )
#                     }

#                     # Add debug printing to verify the relationships
#                     print(f"Series UID: {series.series_instance_uid}")
#                     print(f"Study UID: {study.study_instance_uid}")
#                     print(f"Number of instances: {instances.count()}")

#                     self.df = pd.DataFrame(df_data)
#                     print("Reference DataFrame:")
#                     print(self.df)

#                     # Step 7: Replace all UIDs using callbacks
#                     self.replacement_count = 0
#                     ds.walk(self.frame_of_reference_callback)
#                     ds.walk(self.sop_instance_callback)
                

#                     print(f"Number of SOP Instance UID replacements: {self.replacement_count}")

#                     # Step 8: Save the updated file with unique name directly to target_dir
#                     base_name, extension = os.path.splitext(filename)
#                     unique_filename = f"{base_name}_{str(uuid.uuid4())[:8]}{extension}"
#                     output_path = os.path.join(target_dir, unique_filename)  # Save directly to target_dir
#                     ds.save_as(output_path)
#                     print(f"Saved reidentified file: {output_path}")

#                     # Step 9: Update or create RTStructFile record
#                     rtstruct_file, created = RTStructFile.objects.update_or_create(
#                         series_instance_uid=ds.SeriesInstanceUID,
#                         original_file_path=file_path,
#                         defaults={
#                             'dicom_series': self.series,
#                             'processed_file_path': output_path,
#                             'processing_date': date.today(),
#                             'processing_status': 'SUCCESS'
#                         }
#                     )
#                     print(f"Updated database record for RTStructFile: {rtstruct_file.series_instance_uid}")

#                 except Exception as e:
#                     print(f"Error processing file {file_path}: {str(e)}")
#                     # Update database with error status
#                     try:
#                         RTStructFile.objects.update_or_create(
#                             series_instance_uid=ds.SeriesInstanceUID if 'ds' in locals() else 'UNKNOWN',
#                             original_file_path=file_path,
#                             defaults={
#                                 'dicom_series': self.series if hasattr(self, 'series') else None,
#                                 'processing_date': date.today(),
#                                 'processing_status': f'ERROR: {str(e)}'
#                             }
#                         )
#                     except Exception as db_error:
#                         print(f"Error updating database: {str(db_error)}")
                    
#                 print(f"Completed processing of {file_path}")  # Debug line

#         print("Finished processing all files")  # Debug line
