import os
import yaml
import glob
import shutil
import hashlib
import pydicom
import numpy as np
import pandas as pd
from datetime import datetime
from django.utils import timezone
from dicom_handler.models import DicomSeriesProcessing, ModelYamlInfo, Rule, RuleSet, DicomUnprocessed, ProcessingStatus

def get_all_files(directory_path):
    if not os.path.exists(directory_path):
        print(f"Directory does not exist: {directory_path}")
        return []
       
    if not os.path.isdir(directory_path):
        print(f"Path is not a directory: {directory_path}")
        return []
   
    all_files = []
   
    print(f"Searching in directory: {directory_path}")
   
    for root, dirs, files in os.walk(directory_path):
        print(f"Current directory: {root}")
        print(f"Found files: {files}")
       
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
            print(f"Added file: {file_path}")
           
    print(f"Total files found: {len(all_files)}")
    print(all_files)
    return all_files

def update_dicom_tags(dicom_path, tags_to_check):
    dicom_data = pydicom.dcmread(dicom_path)

    for tag in tags_to_check:
        print(f"Checking tag: {tag}")
        if tag in dicom_data:
            field_value = dicom_data.get(tag)
            if field_value is None or str(field_value).strip() == "":
                print(f"Empty/None value found for {tag}, setting to NaN")
                dicom_data[tag] = np.NaN
        else:
            print(f"Tag {tag} not found in DICOM file")
            dicom_data = "-"
    
    print("Finished updating DICOM tags")
    return dicom_data

def dicom_series_separation(sourcedir, processeddir):
    print("\n=== Starting DICOM Series Separation ===")
    print(f"Source Directory: {sourcedir}")
    print(f"Processing Directory: {processeddir}")
    
    try:
        print("\nGetting list of files...")
        filespath = get_all_files(sourcedir)
        print(f"Found {len(filespath)} files to process")
        
        try:
            for i, file in enumerate(filespath, 1):
                print("Reading DICOM file...")
                dcm = pydicom.dcmread(file)
                
                if dcm.Modality == "CT" or dcm.Modality == "MR":
                    print(f"Found valid modality: {dcm.Modality}")
                    
                    patient_id = dcm.PatientID
                    patient_id = patient_id.replace("/", "_")
                    seriesUID = dcm.SeriesInstanceUID
                    sopinstanceUID = dcm.SOPInstanceUID

                    patient_dir = os.path.join(processeddir, patient_id)
                    separated_series_dir = os.path.join(processeddir, f"{patient_dir}-{seriesUID}")

                    series_exists = DicomSeriesProcessing.objects.filter(sop_instance_uid=sopinstanceUID).exists()
                    print(f"SOP Instance UID exists: {sopinstanceUID}")
                    if not series_exists:
                        
                        print("\n=== DICOM Details ===")
                        print(f"Patient ID: {getattr(dcm, 'PatientID', '')}")
                        print(f"Patient Name: {getattr(dcm, 'PatientName', '')}")
                        print(f"Gender: {getattr(dcm, 'PatientSex', '')}")
                        print(f"Study UID: {getattr(dcm, 'StudyInstanceUID', '')}")
                        print(f"Series UID: {getattr(dcm, 'SeriesInstanceUID', '')}")
                        print(f"File Path: {file}")
                        print(f"Study Date: {getattr(dcm, 'StudyDate', '')}")
                        print(f"Modality: {getattr(dcm, 'Modality', '')}")
                        print(f"Protocol: {getattr(dcm, 'ProtocolName', '')}")
                        print(f"Description: {getattr(dcm, 'SeriesDescription', '')}")
                        print("-" * 50)

                        print("\nCreating DicomSeriesProcessing record...")
                        series_obj = DicomSeriesProcessing.objects.create(
                            patientid = getattr(dcm, 'PatientID', ''),
                            patientname = getattr(dcm, 'PatientName', ''),
                            gender = getattr(dcm, 'PatientSex', ''),
                            studyid = getattr(dcm, 'StudyInstanceUID', ''),
                            seriesid = getattr(dcm, 'SeriesInstanceUID', ''),
                            seriesfilepath = file,
                            studydate = getattr(dcm, 'StudyDate', ''),
                            modality = getattr(dcm, 'Modality', ''),
                            protocol = getattr(dcm, 'ProtocolName', ''),
                            sop_instance_uid = getattr(dcm, 'SOPInstanceUID', ''),
                            description = getattr(dcm, 'SeriesDescription', ''),
                            processing_start = timezone.now()
                        )
                        
                        print("Successfully created DicomSeriesProcessing record")
                        print(f"\nCreating directory: {separated_series_dir}")
                        os.makedirs(separated_series_dir, exist_ok=True)
                        
                        print(f"Copying file to: {separated_series_dir}")
                        shutil.copy2(file, separated_series_dir)
                        
                        DicomSeriesProcessing.objects.filter(id=series_obj.id).update(
                            series_split_done = True,
                            processing_end = timezone.now()
                        )
                        print("File copy complete")
                    else:
                        # print(f"Skipping file - invalid modality: {dcm.Modality}")
                        pass

        except Exception as e:
            print("\nError processing DICOM object")
            print(f"Error details: {str(e)}")
            print(f"Error type: {type(e).__name__}")
    
    except Exception as e:
        print("\nError in main processing loop")
        print(f"Error details: {str(e)}")
        print(f"Error type: {type(e).__name__}")
    
    print("\n=== DICOM Series Separation Complete ===")



# calculate hash value of a file
def calculate_hash(file_path):
    hash_md5 = hashlib.sha512()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


# Read metadata from dicom file
def read_dicom_metadata(dicom_series_path, unprocess_dicom_path, deidentified_dicom_path):
    try:
        ds = pydicom.dcmread(
                os.path.join(
                    dicom_series_path,
                    os.listdir(dicom_series_path)[0])
            )
        processing, created = DicomUnprocessed.objects.update_or_create(
            patientid=getattr(ds, 'PatientID', ''),
            patientname=getattr(ds,'PatientName',''),
            gender=getattr(ds, 'PatientSex', ''),
            studydate=datetime.strptime(ds.StudyDate, "%Y%m%d").date() if ds.StudyDate else None,
            description=getattr(ds, 'SeriesDescription', ''),
            modality=getattr(ds, 'Modality', ''),
            protocol=getattr(ds, 'ProtocolName', ''),
            studyid=ds.StudyInstanceUID,
            seriesid=ds.SeriesInstanceUID
        )
        print(f"Processing studydate: {processing.studydate}")


        yaml_files = glob.glob(os.path.join(dicom_series_path, "*.yml"))
        print(yaml_files)
        if len(yaml_files) == 1:
            yaml_file_path = yaml_files[0]
            yaml_file_hash = calculate_hash(yaml_file_path)

            # Check if the YAML file hash already exists in the database
            if ModelYamlInfo.objects.filter(file_hash=yaml_file_hash).exists():
                yaml_file_name = ModelYamlInfo.objects.get(file_hash=yaml_file_hash).yaml_name
                print(f"YAML file name: {yaml_file_name}")
                print("YAML file hash already exists in the database.")
                
                # move folder to unprocess dicom
                shutil.move(dicom_series_path, deidentified_dicom_path)

                DicomUnprocessed.objects.filter(id = processing.id).update(
                    series_folder_location = deidentified_dicom_path
                )
                
                ProcessingStatus.objects.create(
                    patient_id = DicomUnprocessed.objects.get(id = processing.id),
                    status = f"{yaml_file_name} Template file matched",
                    dicom_move_folder_status = "Move to Deidentification Folder",
                )

            else:
                print("protocol key does not exist") # move folder to unprocess dicom
                shutil.move(dicom_series_path, unprocess_dicom_path)

                ProcessingStatus.objects.create(
                    patient_id = DicomUnprocessed.objects.get(id = processing.id),
                    status = f"Invalid Template file",
                    dicom_move_folder_status = "Move to Unprocessed Folder",
                )

                DicomUnprocessed.objects.filter(id = processing.id).update(
                    series_folder_location = unprocess_dicom_path,
                    unprocessed = True
                )

        elif len(yaml_files) == 0:
            try:
                ds = pydicom.dcmread(
                    os.path.join(dicom_series_path, os.listdir(dicom_series_path)[0])
                )
                tag_list = []
                for elem in ds:
                    # Create a dictionary for the current element
                    tag_dict = {
                        'tag': str(elem.tag),
                        'tag_name': elem.name.replace(" ", ""),
                        'tag_value': str(elem.value)
                    }
                    tag_list.append(tag_dict)
                    # print(tag_dict)

                # Create DataFrame from the list of dictionaries
                tag_df = pd.DataFrame(tag_list)
                tag_df["patient_id"] = ds.PatientID
                # print(tag_df)

                # fatch rule table
                rule_set_table = Rule.objects.all().values(
                    "rule_set__id","rule_set__rule_set_name", "tag_name__tag_name", "tag_value"
                )
                rule_set_table_df = pd.DataFrame(list(rule_set_table))
                rule_set_table_df["count_rule"] = rule_set_table_df.groupby("rule_set__id")["rule_set__id"].transform("count")
                rule_set_table_df.rename(columns={"tag_name__tag_name": "tag_name", "tag_value": "tag_value"}, inplace=True)
                # print(rule_set_table_df)
                join_df = pd.merge(tag_df, rule_set_table_df, on=['tag_name','tag_value']).dropna()

                # join_df = pd.merge(tag_df, rule_set_table_df,on=['tag_name']) #.dropna()
                print(join_df)

                match_rule = join_df.groupby(["rule_set__id", "patient_id", "count_rule"]).count().reset_index()
                match_rule = match_rule[["rule_set__id", "patient_id", "count_rule", "rule_set__rule_set_name"]]
                match_rule.rename(columns={"rule_set__rule_set_name": "match_rule"}, inplace=True)
                
                print(match_rule)
                filter_match_rule = match_rule.loc[(match_rule["count_rule"]) == (match_rule["match_rule"])]

                print(len(filter_match_rule))
                # if len(match_rule["count_rule"] == match_rule["match_rule"])
                if len(filter_match_rule) == 1:

                    model_yaml_path  = RuleSet.objects.filter(
                        id=filter_match_rule["rule_set__id"].unique()[0]
                    ).values("model_yaml__yaml_path").first()["model_yaml__yaml_path"]

                    model_yaml_name  = RuleSet.objects.filter(
                        id=filter_match_rule["rule_set__id"].unique()[0]
                    ).values("model_yaml__yaml_name").first()["model_yaml__yaml_name"]

                    shutil.copy2(
                        model_yaml_path,
                        os.path.join(dicom_series_path)
                    )

                    print(model_yaml_path)
                    shutil.move(dicom_series_path, deidentified_dicom_path)

                    ProcessingStatus.objects.create(
                        patient_id = DicomUnprocessed.objects.get(id = processing.id),
                        status = f"{model_yaml_name} Template file Attached",
                        yaml_attach_status = "Yaml file attached",
                        dicom_move_folder_status = "Move to Deidentification Folder"
                    )

                    DicomUnprocessed.objects.filter(id = processing.id).update(
                        series_folder_location = deidentified_dicom_path)
                    
                elif len(filter_match_rule) > 1:
                    print("Multiple rule set match series data move to dicom unprocessed folder")
                    shutil.move(dicom_series_path, unprocess_dicom_path)

                    print(filter_match_rule)
                    rule_set_table_df.merge(filter_match_rule, on = "rule_set__id", how = "right")
                    print(rule_set_table_df)
                    print("-" *20)
                    print(filter_match_rule)
                    multiple_rules = ', '.join(rule_set_table_df["rule_set__rule_set_name"].unique().tolist())
                    print(multiple_rules)
                    ProcessingStatus.objects.create(
                        patient_id = DicomUnprocessed.objects.get(id = processing.id),
                        status = f"Rule Sets Matched : {multiple_rules}",
                        dicom_move_folder_status = "Move to Unprocessed Folder", 
                    )

                    DicomUnprocessed.objects.filter(id = processing.id).update(
                        series_folder_location = unprocess_dicom_path,
                        unprocessed = True
                    )
                else:
                    shutil.move(dicom_series_path, unprocess_dicom_path)
                    ProcessingStatus.objects.create(
                        patient_id = DicomUnprocessed.objects.get(id = processing.id),
                        status = "No Rule Sets Matched",
                        dicom_move_folder_status = "Move to Unprocessed Folder", 
                    )

                    DicomUnprocessed.objects.filter(id = processing.id).update(
                        series_folder_location = unprocess_dicom_path,
                        unprocessed = True
                    )

               
            except Exception as e:
                print(e)

        else:
            # if multiple yaml file found then the folder will move to unprocess dicom
            shutil.move(dicom_series_path, unprocess_dicom_path)

            ProcessingStatus.objects.create(
                patient_id = DicomUnprocessed.objects.get(id = processing.id),
                status = f"Multiple Yaml file in folder",
                dicom_move_folder_status = "Move to Unprocessed Folder"
            )

            
            DicomUnprocessed.objects.filter(id = processing.id).update(
                series_folder_location = unprocess_dicom_path,
                unprocessed = True
            )

    except Exception as e:
        print("error")
        print(e)
    
