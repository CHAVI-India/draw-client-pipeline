

import os
import shutil
import pydicom
# from loguru import logger
from datetime import datetime
# from dbconnection import insert_data
# from .dicomseriesprocessing import update_dicom_tags
from dicom_handler.models import *


def get_seriesUID_from_rtstruct(ds):
    if 'ReferencedFrameOfReferenceSequence' in ds:
        for i in ds.ReferencedFrameOfReferenceSequence:
            if 'RTReferencedStudySequence' in i:
                for j in i.RTReferencedStudySequence:
                    if 'RTReferencedSeriesSequence' in j:
                        for k in j.RTReferencedSeriesSequence:
                            if 'SeriesInstanceUID' in k:
                                # Print the SeriesInstanceUID directly
                                SeriesInstanceUID = k.SeriesInstanceUID

    return SeriesInstanceUID

def find_pred_rt_files(root_folder, send_remote_folder):
    for protocol_folder in os.listdir(root_folder):
        protocol_folder_path = os.path.join(root_folder, protocol_folder)
        for folder_name, subfolders, files in os.walk(protocol_folder_path):
            if "results" not in folder_name:
                continue
            for file in files:
                try:
                    if file.endswith('.dcm'):  # Corrected this line
                        file_path = os.path.join(folder_name, file)
                        # Read DICOM file
                        ds = pydicom.dcmread(file_path)
                        # Get patient ID and replace backslashes with underscores
                        patient_id = ds.PatientID.replace("/", "_")
                        sop = ds.SOPInstanceUID
                        # seriesid = getattr(ds, 'SeriesInstanceUID', ''),
                        seriesid = get_seriesUID_from_rtstruct(ds)
                        
                        if ds.Modality == "RTSTRUCT":
                            # Check if a folder with patient ID exists
                            patient_folder = os.path.join(send_remote_folder, patient_id)
                            if os.path.exists(patient_folder):
                                dest_path = os.path.join(patient_folder, file)  # Destination path with original file name
                                newname = f"DRAW_{patient_id}_{sop}.dcm"
                                dest_path_newname = os.path.join(patient_folder, newname)
                                try:
                                    if not os.path.exists(dest_path_newname):
                                        shutil.copy2(file_path, dest_path)  # Copying the file with original name to destination folder
                                        newname = f"DRAW_{patient_id}_{sop}.dcm"  # New name without folder name prefix
                                        new_path = os.path.join(patient_folder, newname)  # Full path to the new name in destination folder
                                        os.rename(dest_path, new_path)  # Renaming the file within the destination folder

                                        ProcessingStatus.objects.create(
                                            patient_id = DicomUnprocessed.objects.get(seriesid = seriesid),
                                            status = f"Structure Set Created",
                                            dicom_move_folder_status = "Move to Data Store",
                                        )

                                        print(f"File copied and renamed in destination folder: {new_path}")
                                    else:
                                        print(f"file path already exists")
                                except FileExistsError:
                                    print(f"File already exists in destination folder: {dest_path}")
                            else:
                                print(f"Folder with patient ID does not exist: {patient_id}")
                
                except Exception as e:
                    print(e)



