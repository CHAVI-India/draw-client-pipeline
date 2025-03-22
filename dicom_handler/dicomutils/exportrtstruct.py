import os
import shutil
import pydicom
from datetime import datetime
from dicom_handler.models import *
import logging

# Get logger
logger = logging.getLogger('dicom_handler_logs')

def get_seriesUID_from_rtstruct(ds):
    """Extract SeriesInstanceUID from RTSTRUCT DICOM file."""
    logger.debug("Extracting SeriesInstanceUID from RTSTRUCT")
    try:
        if 'ReferencedFrameOfReferenceSequence' in ds:
            for i in ds.ReferencedFrameOfReferenceSequence:
                if 'RTReferencedStudySequence' in i:
                    for j in i.RTReferencedStudySequence:
                        if 'RTReferencedSeriesSequence' in j:
                            for k in j.RTReferencedSeriesSequence:
                                if 'SeriesInstanceUID' in k:
                                    SeriesInstanceUID = k.SeriesInstanceUID
                                    logger.info(f"Successfully extracted SeriesInstanceUID: {SeriesInstanceUID}")
                                    return SeriesInstanceUID
        
        logger.warning("Required DICOM sequences not found for SeriesInstanceUID extraction")
        return None
    
    except Exception as e:
        logger.error(f"Error extracting SeriesInstanceUID: {str(e)}")
        raise

def find_pred_rt_files(root_folder, send_remote_folder):
    """Find and process predicted RT structure files."""
    logger.info(f"Starting RT file processing from {root_folder} to {send_remote_folder}")
    
    try:
        for protocol_folder in os.listdir(root_folder):
            protocol_folder_path = os.path.join(root_folder, protocol_folder)
            logger.debug(f"Processing protocol folder: {protocol_folder}")
            
            for folder_name, subfolders, files in os.walk(protocol_folder_path):
                if "results" not in folder_name:
                    logger.debug(f"Skipping non-results folder: {folder_name}")
                    continue
                
                logger.debug(f"Processing results folder: {folder_name}")
                for file in files:
                    try:
                        if file.endswith('.dcm'):
                            file_path = os.path.join(folder_name, file)
                            logger.debug(f"Processing DICOM file: {file_path}")
                            
                            # Read DICOM file
                            ds = pydicom.dcmread(file_path)
                            patient_id = ds.PatientID.replace("/", "_")
                            sop = ds.SOPInstanceUID
                            seriesid = get_seriesUID_from_rtstruct(ds)
                            
                            logger.debug(f"DICOM details - Patient ID: {patient_id}, SOP: {sop}, Series ID: {seriesid}")
                            
                            if ds.Modality == "RTSTRUCT":
                                patient_folder = os.path.join(send_remote_folder, patient_id)
                                logger.debug(f"Processing RTSTRUCT for patient folder: {patient_folder}")
                                
                                if os.path.exists(patient_folder):
                                    dest_path = os.path.join(patient_folder, file)
                                    newname = f"DRAW_{patient_id}_{sop}.dcm"
                                    dest_path_newname = os.path.join(patient_folder, newname)
                                    
                                    try:
                                        if not os.path.exists(dest_path_newname):
                                            logger.info(f"Copying file to: {dest_path}")
                                            shutil.copy2(file_path, dest_path)
                                            
                                            new_path = os.path.join(patient_folder, newname)
                                            logger.info(f"Renaming file to: {new_path}")
                                            os.rename(dest_path, new_path)
                                            
                                            ProcessingStatus.objects.create(
                                                patient_id=DicomUnprocessed.objects.get(seriesid=seriesid),
                                                status="Structure Set Created",
                                                dicom_move_folder_status="Move to Data Store",
                                            )
                                            logger.info(f"Successfully processed and moved file: {new_path}")
                                        else:
                                            logger.warning(f"File already exists: {dest_path_newname}")
                                    
                                    except FileExistsError:
                                        logger.warning(f"File already exists in destination: {dest_path}")
                                    except Exception as e:
                                        logger.error(f"Error processing file {file}: {str(e)}")
                                else:
                                    logger.warning(f"Patient folder does not exist: {patient_folder}")
                    
                    except Exception as e:
                        logger.error(f"Error processing file {file}: {str(e)}")
                        continue
    
    except Exception as e:
        logger.error(f"Error in find_pred_rt_files: {str(e)}")
        raise

    logger.info("Completed RT file processing")