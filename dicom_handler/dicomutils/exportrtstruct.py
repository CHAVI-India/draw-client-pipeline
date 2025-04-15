import os
import shutil
import pydicom
from datetime import datetime
from dicom_handler.models import DicomSeriesProcessing, CopyDicom, DicomUnprocessed, ProcessingStatus
import logging
from django.conf import settings
# Get logger
logger = logging.getLogger(__name__)


def export_rtstruct():
    """
    This function will export the RTSTRUCT files from the processing folder to the datastore folder in the folder of the patient.
    The steps will be as follows:
    1. It will first get the files from the folder called folder_identified_rtstruct.
    2. For each file it will first if the file is RTStructure File.
    3. It will extract the Referenced Series Instance UID from the file into a variable called referencedseriesuid. Note that this is the referenced series uid not the series instance uid of the RTStructure file. This is available as the tag (0x0020, 0x000E) in the DICOM file and is a nested tag.
    4. It will then check the model called DicomSeriesProcessing and match the value of the seriesid field with the value of the referencedseriesuid variable. 
    5. If it finds a match then it gets the path in the origin_folder_path field.
    6. It will then to the table called CopyDicom and match the value of the destinationdirname field with the path in the origin_folder_path field.
    7. If the value matches then it will copy the file to the destination folder  
    8. As the folder modification date time will be changed it will also update the table called CopyDicom with the new modification date time in the field called dirmodifieddate.
    9. It will also match the value of the seriesid field in the DicomUnprocessed table with the value of the referencedseriesuid variable it will update the value of the status field of the referenced ProcessingStatus table to 'Structure Set Created'.
    """
    logger.info("Starting export_rtstruct function")
    
    # Define source folder for RTSTRUCT files
    source_folder = os.path.join(settings.BASE_DIR, "folder_identified_rtstruct")


    
    try:
        #Check the source folder exists. If not the function will return False.
        if not os.path.exists(source_folder):
            logger.error(f"Source folder {source_folder} does not exist")
            return False
        
        # Get list of files in the folder
        files = os.listdir(source_folder)
        logger.info(f"Found {len(files)} files in {source_folder}")
        
        for file in files:
            file_path = os.path.join(source_folder, file)
            logger.debug(f"Processing file: {file_path}")
            
            # Skip if not a file
            if not os.path.isfile(file_path):
                logger.debug(f"Skipping {file_path} as it's not a file")
                continue
            
            try:
                # Read DICOM file
                logger.debug(f"Reading DICOM file: {file_path}")
                ds = pydicom.dcmread(file_path)
                
                # Check if it's an RTSTRUCT file
                if ds.Modality != "RTSTRUCT":
                    logger.debug(f"Skipping {file_path} as it's not an RTSTRUCT file")
                    continue
                
                logger.info(f"Processing RTSTRUCT file: {file_path}")
                
                # Extract Referenced Series Instance UID
                referencedseriesuid = None
                try:
                    # Navigate nested tags to find SeriesInstanceUID
                    if hasattr(ds, 'ReferencedFrameOfReferenceSequence'):
                        for ref_frame in ds.ReferencedFrameOfReferenceSequence:
                            if hasattr(ref_frame, 'RTReferencedStudySequence'):
                                for ref_study in ref_frame.RTReferencedStudySequence:
                                    if hasattr(ref_study, 'RTReferencedSeriesSequence'):
                                        for ref_series in ref_study.RTReferencedSeriesSequence:
                                            if hasattr(ref_series, 'SeriesInstanceUID'):
                                                referencedseriesuid = ref_series.SeriesInstanceUID
                                                break
                    
                    if not referencedseriesuid:
                        logger.warning(f"Could not find Referenced Series Instance UID in {file_path}")
                        continue
                    
                    logger.info(f"Found Referenced Series Instance UID: {referencedseriesuid}")
                    
                except Exception as e:
                    logger.error(f"Error extracting Referenced Series Instance UID: {str(e)}")
                    continue
                
                # Find matching series in DicomSeriesProcessing
                try:
                    series = DicomSeriesProcessing.objects.filter(seriesid=referencedseriesuid).first()
                    if not series:
                        logger.warning(f"No matching series found for UID: {referencedseriesuid}")
                        continue
                    
                    series_path = series.origin_folder_path
                    logger.info(f"Found matching series with path: {series_path}")
                    
                    # Find matching entry in CopyDicom
                    copy_dicom = CopyDicom.objects.filter(destinationdirname=series_path).first()
                    if not copy_dicom:
                        logger.warning(f"No matching CopyDicom entry found for path: {series_path}")
                        continue
                    
                    destination_dir = copy_dicom.sourcedirname
                    logger.info(f"Found matching CopyDicom with destination: {destination_dir}")
                    
                    # Copy file to destination
                    if not os.path.exists(destination_dir):
                        logger.warning(f"Destination directory {destination_dir} does not exist")
                        continue
                    
                    # Create destination file path
                    destination_file = os.path.join(destination_dir, os.path.basename(file_path))
                    
                    # Copy the file
                    logger.info(f"Copying {file_path} to {destination_file}")
                    shutil.copy2(file_path, destination_file)
                    
                    # Update dirmodifieddate in CopyDicom
                    current_time = datetime.now()
                    copy_dicom.dirmodifieddate = current_time
                    copy_dicom.save()
                    logger.info(f"Updated dirmodifieddate for CopyDicom entry to {current_time}")
                    
                    # Update ProcessingStatus
                    # Find matching entry in DicomUnprocessed
                    unprocessed = DicomUnprocessed.objects.filter(seriesid=referencedseriesuid).first()
                    if unprocessed:
                        # Try to get existing ProcessingStatus
                        try:
                            status = ProcessingStatus.objects.get(patient_id=unprocessed)
                            # Update only if record exists
                            status.status = 'Structure Set Created'
                            status.dicom_move_folder_status = 'Moved to DataStore'
                            status.save()
                            logger.info(f"Updated ProcessingStatus for patient_id {unprocessed.id} to 'Structure Set Created'")
                        except ProcessingStatus.DoesNotExist:
                            logger.warning(f"No ProcessingStatus record exists for patient_id {unprocessed.id}, skipping update")
                    else:
                        logger.warning(f"No matching DicomUnprocessed entry found for UID: {referencedseriesuid}")
                
                except Exception as e:
                    logger.error(f"Error processing database operations: {str(e)}")
                    continue
                
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}")
                continue
        
        logger.info("Completed export_rtstruct function")
        return True
        
    except Exception as e:
        logger.error(f"Error in export_rtstruct function: {str(e)}")
        return False




# def get_seriesUID_from_rtstruct(ds):
#     """Extract SeriesInstanceUID from RTSTRUCT DICOM file."""
#     logger.debug("Extracting SeriesInstanceUID from RTSTRUCT")
#     try:
#         if 'ReferencedFrameOfReferenceSequence' in ds:
#             for i in ds.ReferencedFrameOfReferenceSequence:
#                 if 'RTReferencedStudySequence' in i:
#                     for j in i.RTReferencedStudySequence:
#                         if 'RTReferencedSeriesSequence' in j:
#                             for k in j.RTReferencedSeriesSequence:
#                                 if 'SeriesInstanceUID' in k:
#                                     SeriesInstanceUID = k.SeriesInstanceUID
#                                     logger.info(f"Successfully extracted SeriesInstanceUID: {SeriesInstanceUID}")
#                                     return SeriesInstanceUID
        
#         logger.warning("Required DICOM sequences not found for SeriesInstanceUID extraction")
#         return None
    
#     except Exception as e:
#         logger.error(f"Error extracting SeriesInstanceUID: {str(e)}")
#         raise

# def find_pred_rt_files(root_folder, send_remote_folder):
#     """Find and process predicted RT structure files."""
#     logger.info(f"Starting RT file processing from {root_folder} to {send_remote_folder}")
    
#     try:
#         for protocol_folder in os.listdir(root_folder):
#             protocol_folder_path = os.path.join(root_folder, protocol_folder)
#             logger.debug(f"Processing protocol folder: {protocol_folder}")
            
#             for folder_name, subfolders, files in os.walk(protocol_folder_path):
#                 if "results" not in folder_name:
#                     logger.debug(f"Skipping non-results folder: {folder_name}")
#                     continue
                
#                 logger.debug(f"Processing results folder: {folder_name}")
#                 for file in files:
#                     try:
#                         if file.endswith('.dcm'):
#                             file_path = os.path.join(folder_name, file)
#                             logger.debug(f"Processing DICOM file: {file_path}")
                            
#                             # Read DICOM file
#                             ds = pydicom.dcmread(file_path)
#                             patient_id = ds.PatientID.replace("/", "_")
#                             sop = ds.SOPInstanceUID
#                             seriesid = get_seriesUID_from_rtstruct(ds)
                            
#                             logger.debug(f"DICOM details - Patient ID: {patient_id}, SOP: {sop}, Series ID: {seriesid}")
                            
#                             if ds.Modality == "RTSTRUCT":
#                                 patient_folder = os.path.join(send_remote_folder, patient_id)
#                                 logger.debug(f"Processing RTSTRUCT for patient folder: {patient_folder}")
                                
#                                 if os.path.exists(patient_folder):
#                                     dest_path = os.path.join(patient_folder, file)
#                                     newname = f"DRAW_{patient_id}_{sop}.dcm"
#                                     dest_path_newname = os.path.join(patient_folder, newname)
                                    
#                                     try:
#                                         if not os.path.exists(dest_path_newname):
#                                             logger.info(f"Copying file to: {dest_path}")
#                                             shutil.copy2(file_path, dest_path)
                                            
#                                             new_path = os.path.join(patient_folder, newname)
#                                             logger.info(f"Renaming file to: {new_path}")
#                                             os.rename(dest_path, new_path)
                                            
#                                             ProcessingStatus.objects.create(
#                                                 patient_id=DicomUnprocessed.objects.get(seriesid=seriesid),
#                                                 status="Structure Set Created",
#                                                 dicom_move_folder_status="Move to Data Store",
#                                             )
#                                             logger.info(f"Successfully processed and moved file: {new_path}")
#                                         else:
#                                             logger.warning(f"File already exists: {dest_path_newname}")
                                    
#                                     except FileExistsError:
#                                         logger.warning(f"File already exists in destination: {dest_path}")
#                                     except Exception as e:
#                                         logger.error(f"Error processing file {file}: {str(e)}")
#                                 else:
#                                     logger.warning(f"Patient folder does not exist: {patient_folder}")
                    
#                     except Exception as e:
#                         logger.error(f"Error processing file {file}: {str(e)}")
#                         continue
    
#     except Exception as e:
#         logger.error(f"Error in find_pred_rt_files: {str(e)}")
#         raise

#     logger.info("Completed RT file processing")