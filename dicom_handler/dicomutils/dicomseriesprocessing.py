# import os
# import yaml
# import glob
# import shutil
# import hashlib
# import pydicom
# import numpy as np
# import pandas as pd
# from datetime import datetime
# from django.utils import timezone
# from dicom_handler.models import DicomSeriesProcessing, ModelYamlInfo, Rule, RuleSet, DicomUnprocessed, ProcessingStatus
# import logging

# # Get logger
# logger = logging.getLogger('dicom_handler_logs')


# ## Function to get all files in a directory
# def get_all_files(directory_path):
#     logger.debug(f"Starting file search in directory: {directory_path}")
    
#     if not os.path.exists(directory_path):
#         logger.error(f"Directory does not exist: {directory_path}")
#         return []
       
#     if not os.path.isdir(directory_path):
#         logger.error(f"Path is not a directory: {directory_path}")
#         return []
   
#     all_files = []
    
#     try:
#         for root, dirs, files in os.walk(directory_path):
#             logger.debug(f"Scanning directory: {root}")
#             logger.debug(f"Found {len(files)} files")
            
#             for file in files:
#                 file_path = os.path.join(root, file)
#                 all_files.append(file_path)
#                 logger.debug(f"Added file: {file_path}")
        
#         logger.info(f"Total files found: {len(all_files)}")
#         return all_files
    
#     except Exception as e:
#         logger.error(f"Error while searching files: {str(e)}")
#         return []

# ## Update DICOM tags
# def update_dicom_tags(dicom_path, tags_to_check):
#     logger.debug(f"Updating DICOM tags for file: {dicom_path}")
#     try:
#         dicom_data = pydicom.dcmread(dicom_path)

#         for tag in tags_to_check:
#             logger.debug(f"Checking tag: {tag}")
#             if tag in dicom_data:
#                 field_value = dicom_data.get(tag)
#                 if field_value is None or str(field_value).strip() == "":
#                     logger.debug(f"Empty/None value found for {tag}, setting to NaN")
#                     dicom_data[tag] = np.NaN
#             else:
#                 logger.debug(f"Tag {tag} not found in DICOM file")
#                 dicom_data = "-"
        
#         logger.info("Successfully updated DICOM tags")
#         return dicom_data
    
#     except Exception as e:
#         logger.error(f"Error updating DICOM tags: {str(e)}")
#         raise

# ## DICOM Series Separation
# def dicom_series_separation(sourcedir, processeddir):
#     """
#     Separates DICOM files from a source directory into folders by series.
    
#     This function processes DICOM files from a source directory, groups them by
#     SeriesInstanceUID, and copies them into separate series-specific directories.
#     It also creates database entries for each unique series if they don't already exist.
    
#     The function implements a two-pass approach:
#     1. First pass: Groups all DICOM files by their SeriesInstanceUID
#     2. Second pass: Processes each unique series, creating directories and database entries
    
#     Args:
#         sourcedir (str): Source directory containing unsorted DICOM files
#         processeddir (str): Target directory where series-specific folders will be created
        
#     Returns:
#         list: List of paths to all series directories that were created
            
#     Implementation Details:
#     - Only processes files with modalities CT, MR, or PT
#     - Avoids duplicate database entries by checking if series already exists
#     - Creates database entries with DicomSeriesProcessing model for each unique series
#     - Always copies files regardless of whether the series exists in the database
#     - Counts the number of files per series and stores this in the database
#     - Series folders are named as "{patient_dir}-{seriesUID}"
    
#     Database fields populated:
#     - patientid: Patient ID from DICOM
#     - patientname: Patient name from DICOM
#     - gender: Patient sex from DICOM
#     - studyid: Study Instance UID from DICOM
#     - seriesid: Series Instance UID from DICOM
#     - seriesfilepath: Path to first file in the series
#     - studydate: Study date from DICOM
#     - modality: Modality from DICOM
#     - protocol: Protocol name from DICOM
#     - description: Series description from DICOM
#     - dicomcount: Number of files in the series
#     - processing_start/end: Timestamps for processing
#     """
#     logger.info("=== Starting DICOM Series Separation ===")
#     logger.info(f"Source Directory: {sourcedir}")
#     logger.info(f"Processing Directory: {processeddir}")
    
#     # List to store all separated series directory paths
#     separated_series_dirs = []
    
#     try:
#         filespath = get_all_files(sourcedir)
#         logger.info(f"Found {len(filespath)} files to process")
        
#         # Dictionary to group files by series
#         series_groups = {}
        
#         # First pass: Group all files by SeriesInstanceUID
#         for i, file in enumerate(filespath, 1):
#             try:
#                 logger.debug(f"Processing file {i}/{len(filespath)}: {file}")
#                 dcm = pydicom.dcmread(file)
                
#                 if dcm.Modality in ["CT", "MR", "PT"]:
#                     logger.debug(f"Valid modality found: {dcm.Modality}")
                    
#                     seriesUID = dcm.SeriesInstanceUID
                    
#                     # Add to series group
#                     if seriesUID not in series_groups:
#                         series_groups[seriesUID] = {
#                             'files': [],
#                             'first_dcm': dcm,
#                             'first_file_path': file
#                         }
                    
#                     series_groups[seriesUID]['files'].append(file)
                    
#                 else:
#                     logger.debug(f"Skipping file - invalid modality: {dcm.Modality}")

                
#             except Exception as e:
#                 logger.error(f"Error reading file {file}: {e}")
#                 logger.warning(f"Deleting non-DICOM file: {file}")
#                 try:
#                     os.remove(file)
#                     logger.info(f"Successfully deleted: {file}")
#                 except Exception as delete_error:
#                     logger.error(f"Failed to delete file {file}: {delete_error}")
#                 continue
        
#         # Second pass: Process each series once
#         logger.info(f"Found {len(series_groups)} unique series to process")
        
#         for seriesUID, series_data in series_groups.items():
#             try:
#                 dcm = series_data['first_dcm']
#                 file_path = series_data['first_file_path']
#                 files = series_data['files']
                
#                 patient_id = dcm.PatientID.replace("/", "_")
#                 patient_dir = os.path.join(processeddir, patient_id)
#                 separated_series_dir = os.path.join(processeddir, f"{patient_dir}-{seriesUID}")
                
#                 # Always create the directory and copy files for this series
#                 logger.debug(f"Creating series directory and copying files for: {seriesUID}")
#                 os.makedirs(separated_series_dir, exist_ok=True)
                
#                 for dicom_file in files:
#                     shutil.copy2(dicom_file, separated_series_dir)
                
#                 logger.info(f"Successfully copied {len(files)} files to {separated_series_dir}")
                
#                 # Add the series directory path to the list
#                 separated_series_dirs.append(separated_series_dir)
                
#                 # Check if this series already exists in the database - only skip DB creation if it exists
#                 series_exists = DicomSeriesProcessing.objects.filter(seriesid=seriesUID).exists()
                
#                 if not series_exists:
#                     logger.debug(f"Creating new DICOM series processing record for series: {seriesUID}")
                    
#                     # Log DICOM details
#                     logger.info(f"""
#                         DICOM Series Details:
#                         Patient ID: {getattr(dcm, 'PatientID', '')}
#                         Patient Name: {getattr(dcm, 'PatientName', '')}
#                         Study Date: {getattr(dcm, 'StudyDate', '')}
#                         Modality: {getattr(dcm, 'Modality', '')}
#                         Protocol: {getattr(dcm, 'ProtocolName', '')}
#                         Series Description: {getattr(dcm, 'SeriesDescription', '')}
#                         DICOM Count: {len(files)}
#                     """)

#                     try:
#                         # Create a single database entry for the entire series
#                         series_obj = DicomSeriesProcessing.objects.create(
#                             patientid=getattr(dcm, 'PatientID', ''),
#                             patientname=getattr(dcm, 'PatientName', ''),
#                             gender=getattr(dcm, 'PatientSex', ''),
#                             studyid=getattr(dcm, 'StudyInstanceUID', ''),
#                             seriesid=getattr(dcm, 'SeriesInstanceUID', ''),
#                             seriesfilepath=separated_series_dir,
#                             origin_folder_path=sourcedir,
#                             studydate=getattr(dcm, 'StudyDate', ''),
#                             modality=getattr(dcm, 'Modality', ''),
#                             protocol=getattr(dcm, 'ProtocolName', ''),
#                             description=getattr(dcm, 'SeriesDescription', ''),
#                             dicomcount=len(files),
#                             processing_start=timezone.now()
#                         )
                        
#                         logger.info(f"Successfully created DicomSeriesProcessing record for series with {len(files)} files")
                        
#                         # Mark series as processed
#                         DicomSeriesProcessing.objects.filter(id=series_obj.id).update(
#                             series_split_done=True,
#                             processing_end=timezone.now()
#                         )
                        
#                     except Exception as e:
#                         logger.error(f"Error creating/updating database record for series {seriesUID}: {str(e)}")
                
#                 else:
#                     logger.info(f"Series {seriesUID} already exists in database - skipping database creation only")
            
#             except Exception as e:
#                 logger.error(f"Error processing series {seriesUID}: {str(e)}")

#     except Exception as e:
#         logger.error(f"Error in main processing loop: {str(e)}")
    
#     logger.info("=== DICOM Series Separation Complete ===")
    
#     # Return the list of separated series directories
#     return separated_series_dirs


# ## Hash Calculation
# def calculate_hash(file_path):
#     logger.debug(f"Calculating hash for file: {file_path}")
#     try:
#         hash_md5 = hashlib.sha512()
#         with open(file_path, "rb") as f:
#             for chunk in iter(lambda: f.read(4096), b""):
#                 hash_md5.update(chunk)
#         hash_value = hash_md5.hexdigest()
#         logger.debug(f"Hash calculation complete: {hash_value[:10]}...")
#         return hash_value
#     except Exception as e:
#         logger.error(f"Error calculating hash for {file_path}: {str(e)}")
#         raise

# ## DICOM Metadata Reading
# def read_dicom_metadata(dicom_series_path, unprocess_dicom_path, deidentified_dicom_path):
#     logger.info(f"Starting DICOM metadata processing for path: {dicom_series_path}")
#     try:
#         # Read initial DICOM file
#         logger.debug(f"Reading DICOM file from: {dicom_series_path}")
#         ds = pydicom.dcmread(
#                 os.path.join(
#                     dicom_series_path,
#                     os.listdir(dicom_series_path)[0])
#             )

#         # Create or update DicomUnprocessed record
#         logger.debug("Creating/updating DicomUnprocessed record")
#         processing, created = DicomUnprocessed.objects.update_or_create(
#             patientid=getattr(ds, 'PatientID', ''),
#             patientname=getattr(ds,'PatientName',''),
#             gender=getattr(ds, 'PatientSex', ''),
#             studydate=datetime.strptime(ds.StudyDate, "%Y%m%d").date() if ds.StudyDate else None,
#             description=getattr(ds, 'SeriesDescription', ''),
#             modality=getattr(ds, 'Modality', ''),
#             protocol=getattr(ds, 'ProtocolName', ''),
#             studyid=ds.StudyInstanceUID,
#             seriesid=ds.SeriesInstanceUID,
#             ready_for_deidentification=False
#             )
#         logger.info(f"Processing studydate: {processing.studydate}")

#         # Check for YAML files
#         yaml_files = glob.glob(os.path.join(dicom_series_path, "*.yml"))
#         logger.debug(f"Found {len(yaml_files)} YAML files")

#         if len(yaml_files) == 1:
#             logger.debug("Processing single YAML file")
#             yaml_file_path = yaml_files[0]
#             yaml_file_hash = calculate_hash(yaml_file_path)

#             if ModelYamlInfo.objects.filter(file_hash=yaml_file_hash).exists():
#                 yaml_file_name = ModelYamlInfo.objects.get(file_hash=yaml_file_hash).yaml_name
#                 logger.info(f"Matching YAML file found: {yaml_file_name}")

#                 # Check if the directory to which the files will be moved already exists
#                 dest_dir = os.path.join(deidentified_dicom_path, os.path.basename(dicom_series_path))
#                 if os.path.exists(dest_dir):
#                     shutil.rmtree(dest_dir)
#                     logger.info(f"Successfully removed existing directory: {dest_dir}")

#                 logger.debug(f"Moving directory to: {deidentified_dicom_path}")
#                 shutil.move(dicom_series_path, deidentified_dicom_path)
#                 logger.info(f"Successfully moved directory to: {deidentified_dicom_path}")
#                 DicomUnprocessed.objects.filter(id=processing.id).update(
#                     series_folder_location=f"{dest_dir}",
#                     ready_for_deidentification=True
#                 )
                
#                 ProcessingStatus.objects.create(
#                     patient_id=DicomUnprocessed.objects.get(id=processing.id),
#                     status=f"{yaml_file_name} Template file matched",
#                     dicom_move_folder_status="Move to Deidentification Folder",
#                 )

#                 # Set success flags for further processing of the task.
#                 ready_for_deidentification = True
#                 series_folder_location = dest_dir

#                 logger.info("Successfully processed and moved to deidentification folder")
#                 logger.info(f"Series folder location: {series_folder_location}")
#                 logger.info(f"Ready for deidentification: {ready_for_deidentification}")

#             else:
#                 logger.warning("Protocol key does not exist, moving to unprocessed folder")
#                 dest_dir = os.path.join(unprocess_dicom_path, os.path.basename(dicom_series_path))
#                 if os.path.exists(dest_dir):
#                     shutil.rmtree(dest_dir)
#                     logger.info(f"Successfully removed existing directory: {dest_dir}")

#                 logger.info(f"Moving directory to: {unprocess_dicom_path}")

#                 shutil.move(dicom_series_path, unprocess_dicom_path)
#                 logger.info(f"Successfully moved directory to: {unprocess_dicom_path}")
#                 ProcessingStatus.objects.create(
#                     patient_id=DicomUnprocessed.objects.get(id=processing.id),
#                     status="Invalid Template file",
#                     dicom_move_folder_status="Move to Unprocessed Folder",
#                     )

#                 DicomUnprocessed.objects.filter(id=processing.id).update(
#                     series_folder_location=f"{dest_dir}",
#                         unprocessed=True,
#                         ready_for_deidentification=False
#                         )
#                 # Set success flags for further processing of the task.
#                 ready_for_deidentification = False
#                 series_folder_location = dest_dir
#                 logger.info("Successfully processed and moved to unprocessed folder")
#                 logger.info(f"Series folder location: {series_folder_location}")
#                 logger.info(f"Ready for deidentification: {ready_for_deidentification}")

#         elif len(yaml_files) == 0:
#             logger.debug("No YAML files found, processing DICOM tags")
#             try:
#                 ds = pydicom.dcmread(
#                     os.path.join(dicom_series_path, os.listdir(dicom_series_path)[0])
#                 )
                
#                 # Process DICOM tags
#                 logger.debug("Processing DICOM tags")
#                 tag_list = []
#                 for elem in ds:
#                     tag_dict = {
#                         'tag': str(elem.tag),
#                         'tag_name': elem.name.replace(" ", ""),
#                         'tag_value': str(elem.value)
#                     }
#                     tag_list.append(tag_dict)

#                 # Create and process DataFrames
#                 logger.debug("Creating and processing DataFrames")
#                 tag_df = pd.DataFrame(tag_list)
#                 tag_df["patient_id"] = ds.PatientID

#                 rule_set_table = Rule.objects.all().values(
#                     "rule_set__id","rule_set__rule_set_name", "tag_name__tag_name", "tag_value"
#                 )
#                 rule_set_table_df = pd.DataFrame(list(rule_set_table))
#                 rule_set_table_df["count_rule"] = rule_set_table_df.groupby("rule_set__id")["rule_set__id"].transform("count")
#                 rule_set_table_df.rename(columns={"tag_name__tag_name": "tag_name", "tag_value": "tag_value"}, inplace=True)

#                 join_df = pd.merge(tag_df, rule_set_table_df, on=['tag_name','tag_value']).dropna()
#                 logger.debug(f"Merged DataFrame size: {len(join_df)}")

#                 match_rule = join_df.groupby(["rule_set__id", "patient_id", "count_rule"]).count().reset_index()
#                 match_rule = match_rule[["rule_set__id", "patient_id", "count_rule", "rule_set__rule_set_name"]]
#                 match_rule.rename(columns={"rule_set__rule_set_name": "match_rule"}, inplace=True)
                
#                 filter_match_rule = match_rule.loc[(match_rule["count_rule"]) == (match_rule["match_rule"])]
#                 logger.info(f"Found {len(filter_match_rule)} matching rules")

#                 if len(filter_match_rule) == 1:
#                     logger.info("Single rule match found, processing")
#                     model_yaml_path = RuleSet.objects.filter(
#                         id=filter_match_rule["rule_set__id"].unique()[0]
#                     ).values("model_yaml__yaml_path").first()["model_yaml__yaml_path"]

#                     model_yaml_name = RuleSet.objects.filter(
#                         id=filter_match_rule["rule_set__id"].unique()[0]
#                     ).values("model_yaml__yaml_name").first()["model_yaml__yaml_name"]

#                     # Check if the directory to which the files will be moved already exists
#                     dest_dir = os.path.join(deidentified_dicom_path, os.path.basename(dicom_series_path))
#                     if os.path.exists(dest_dir):
#                         shutil.rmtree(dest_dir)
#                         logger.info(f"Successfully removed existing directory: {dest_dir}")                    

#                     logger.debug(f"Copying YAML file: {model_yaml_path}")
#                     shutil.copy2(
#                         model_yaml_path,
#                         os.path.join(dicom_series_path)
#                     )
#                     logger.info(f"Successfully copied YAML file to: {dicom_series_path}")

#                     logger.debug(f"Moving directory to: {deidentified_dicom_path}")
#                     shutil.move(dicom_series_path, deidentified_dicom_path)
#                     logger.info(f"Successfully moved directory to: {deidentified_dicom_path}")
#                     ProcessingStatus.objects.create(
#                         patient_id=DicomUnprocessed.objects.get(id=processing.id),
#                         status=f"{model_yaml_name} Template file Attached",
#                         yaml_attach_status="Yaml file attached",
#                         dicom_move_folder_status="Move to Deidentification Folder",
#                         )

#                     DicomUnprocessed.objects.filter(id=processing.id).update(
#                         series_folder_location=f"{dest_dir}",
#                         ready_for_deidentification=True
#                         )
#                     # Set success flags for furthe processing of the task.

#                     ready_for_deidentification = True
#                     series_folder_location = dest_dir

#                     logger.info("Successfully processed and moved to deidentification folder")
#                     logger.info(f"Series folder location: {series_folder_location}")
#                     logger.info(f"Ready for deidentification: {ready_for_deidentification}")
                    
                    
#                 elif len(filter_match_rule) > 1:
#                     logger.warning("Multiple rule matches found")
#                     dest_dir = os.path.join(unprocess_dicom_path, os.path.basename(dicom_series_path))
#                     if os.path.exists(dest_dir):
#                         shutil.rmtree(dest_dir)
#                         logger.info(f"Successfully removed existing directory: {dest_dir}")

#                     logger.info(f"Moving directory to: {unprocess_dicom_path}")
#                     shutil.move(dicom_series_path, unprocess_dicom_path)
#                     logger.info(f"Successfully moved directory to: {unprocess_dicom_path}")
#                     multiple_rules = ', '.join(rule_set_table_df["rule_set__rule_set_name"].unique().tolist())
#                     logger.info(f"Matched rules: {multiple_rules}")

#                     ProcessingStatus.objects.create(
#                         patient_id=DicomUnprocessed.objects.get(id=processing.id),
#                         status=f"Rule Sets Matched : {multiple_rules}",
#                         dicom_move_folder_status="Move to Unprocessed Folder", 
                        
#                     )

#                     DicomUnprocessed.objects.filter(id=processing.id).update(
#                         series_folder_location=f"{dest_dir}",
#                         unprocessed=True,
#                         ready_for_deidentification=False
#                     )
#                     # Set success flags for further processing of the task.
#                     ready_for_deidentification = False
#                     series_folder_location = dest_dir
#                     logger.info("Successfully processed and moved to unprocessed folder")
#                     logger.info(f"Series folder location: {series_folder_location}")
#                     logger.info(f"Ready for deidentification: {ready_for_deidentification}")
#                 else:
#                     logger.warning("No matching rules found")
#                     dest_dir = os.path.join(unprocess_dicom_path, os.path.basename(dicom_series_path))
#                     if os.path.exists(dest_dir):
#                         shutil.rmtree(dest_dir)
#                         logger.info(f"Successfully removed existing directory: {dest_dir}")

#                     logger.info(f"Moving directory to: {unprocess_dicom_path}")
#                     shutil.move(dicom_series_path, unprocess_dicom_path)
#                     ProcessingStatus.objects.create(
#                         patient_id=DicomUnprocessed.objects.get(id=processing.id),
#                         status="No Rule Sets Matched",
#                         dicom_move_folder_status="Move to Unprocessed Folder",          
                        
#                     )

#                     DicomUnprocessed.objects.filter(id=processing.id).update(
#                         series_folder_location=f"{dest_dir}",
#                         unprocessed=True,
#                         ready_for_deidentification=False
#                     )
#                     # Set success flags for further processing of the task.
#                     ready_for_deidentification = False
#                     series_folder_location = dest_dir
#                     logger.info("Successfully processed and moved to unprocessed folder")
#                     logger.info(f"Series folder location: {series_folder_location}")
#                     logger.info(f"Ready for deidentification: {ready_for_deidentification}")

#             except Exception as e:
#                 logger.error(f"Error processing DICOM tags: {str(e)}")
#                 raise

#         else:
#             logger.warning(f"Multiple YAML files found ({len(yaml_files)}), moving to unprocessed folder")
#             dest_dir = os.path.join(unprocess_dicom_path, os.path.basename(dicom_series_path))
#             if os.path.exists(dest_dir):
#                 shutil.rmtree(dest_dir)
#                 logger.info(f"Successfully removed existing directory: {dest_dir}")

#             logger.info(f"Moving directory to: {unprocess_dicom_path}")
#             shutil.move(dicom_series_path, unprocess_dicom_path)

#             ProcessingStatus.objects.create(
#                 patient_id=DicomUnprocessed.objects.get(id=processing.id),
#                 status="Multiple Yaml file in folder",
#                 dicom_move_folder_status="Move to Unprocessed Folder",
#                 ready_for_deidentification=False
#                 )

#             DicomUnprocessed.objects.filter(id=processing.id).update(
#                 series_folder_location=f"{dest_dir}",
#                 unprocessed=True,
#                 ready_for_deidentification=False
#                 )
#             # Set success flags for further processing of the task.
#             ready_for_deidentification = False
#             series_folder_location = dest_dir
#             logger.info("Successfully processed and moved to unprocessed folder")
#             logger.info(f"Series folder location: {series_folder_location}")
#             logger.info(f"Ready for deidentification: {ready_for_deidentification}")

#     except Exception as e:
#         logger.error(f"Error in read_dicom_metadata: {str(e)}")
#         raise

#     logger.info("Completed DICOM metadata processing")
#     return {
#         "success": ready_for_deidentification,
#         "deidentification_path": series_folder_location
#     }