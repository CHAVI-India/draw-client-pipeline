
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
import logging

# Get logger
logger = logging.getLogger('django_log_lens.client')


## Function to get all files in a directory
def get_all_files(directory_path):
    logger.debug(f"Starting file search in directory: {directory_path}")
    
    if not os.path.exists(directory_path):
        logger.error(f"Directory does not exist: {directory_path}")
        return []
       
    if not os.path.isdir(directory_path):
        logger.error(f"Path is not a directory: {directory_path}")
        return []
   
    all_files = []
    
    try:
        for root, dirs, files in os.walk(directory_path):
            logger.debug(f"Scanning directory: {root}")
            logger.debug(f"Found {len(files)} files")
            
            for file in files:
                file_path = os.path.join(root, file)
                all_files.append(file_path)
                logger.debug(f"Added file: {file_path}")
        
        logger.info(f"Total files found: {len(all_files)}")
        return all_files
    
    except Exception as e:
        logger.error(f"Error while searching files: {str(e)}")
        return []

## Update DICOM tags
def update_dicom_tags(dicom_path, tags_to_check):
    logger.debug(f"Updating DICOM tags for file: {dicom_path}")
    try:
        dicom_data = pydicom.dcmread(dicom_path)

        for tag in tags_to_check:
            logger.debug(f"Checking tag: {tag}")
            if tag in dicom_data:
                field_value = dicom_data.get(tag)
                if field_value is None or str(field_value).strip() == "":
                    logger.debug(f"Empty/None value found for {tag}, setting to NaN")
                    dicom_data[tag] = np.NaN
            else:
                logger.debug(f"Tag {tag} not found in DICOM file")
                dicom_data = "-"
        
        logger.info("Successfully updated DICOM tags")
        return dicom_data
    
    except Exception as e:
        logger.error(f"Error updating DICOM tags: {str(e)}")
        raise

## DICOM Series Separation
def dicom_series_separation(sourcedir, processeddir):
    logger.info("=== Starting DICOM Series Separation ===")
    logger.info(f"Source Directory: {sourcedir}")
    logger.info(f"Processing Directory: {processeddir}")
    
    try:
        filespath = get_all_files(sourcedir)
        logger.info(f"Found {len(filespath)} files to process")
        
        for i, file in enumerate(filespath, 1):
            try:
                logger.debug(f"Processing file {i}/{len(filespath)}: {file}")
                dcm = pydicom.dcmread(file)
                
                if dcm.Modality in ["CT", "MR"]:
                    logger.debug(f"Valid modality found: {dcm.Modality}")
                    
                    patient_id = dcm.PatientID.replace("/", "_")
                    seriesUID = dcm.SeriesInstanceUID
                    sopinstanceUID = dcm.SOPInstanceUID

                    patient_dir = os.path.join(processeddir, patient_id)
                    separated_series_dir = os.path.join(processeddir, f"{patient_dir}-{seriesUID}")

                    series_exists = DicomSeriesProcessing.objects.filter(sop_instance_uid=sopinstanceUID).exists()
                    
                    if not series_exists:
                        logger.debug("Creating new DICOM series processing record")
                        
                        # Log DICOM details
                        logger.info(f"""
                            DICOM Details:
                            Patient ID: {getattr(dcm, 'PatientID', '')}
                            Patient Name: {getattr(dcm, 'PatientName', '')}
                            Study Date: {getattr(dcm, 'StudyDate', '')}
                            Modality: {getattr(dcm, 'Modality', '')}
                            Protocol: {getattr(dcm, 'ProtocolName', '')}
                        """)

                        try:
                            series_obj = DicomSeriesProcessing.objects.create(
                                patientid=getattr(dcm, 'PatientID', ''),
                                patientname=getattr(dcm, 'PatientName', ''),
                                gender=getattr(dcm, 'PatientSex', ''),
                                studyid=getattr(dcm, 'StudyInstanceUID', ''),
                                seriesid=getattr(dcm, 'SeriesInstanceUID', ''),
                                seriesfilepath=file,
                                studydate=getattr(dcm, 'StudyDate', ''),
                                modality=getattr(dcm, 'Modality', ''),
                                protocol=getattr(dcm, 'ProtocolName', ''),
                                sop_instance_uid=getattr(dcm, 'SOPInstanceUID', ''),
                                description=getattr(dcm, 'SeriesDescription', ''),
                                processing_start=timezone.now()
                            )
                            
                            logger.info("Successfully created DicomSeriesProcessing record")
                            
                            os.makedirs(separated_series_dir, exist_ok=True)
                            shutil.copy2(file, separated_series_dir)
                            
                            DicomSeriesProcessing.objects.filter(id=series_obj.id).update(
                                series_split_done=True,
                                processing_end=timezone.now()
                            )
                            logger.info(f"Successfully processed and copied file to {separated_series_dir}")
                            
                        except Exception as e:
                            logger.error(f"Error creating/updating database record: {str(e)}")
                    
                    else:
                        logger.debug(f"Skipping existing series: {sopinstanceUID}")
                
                else:
                    logger.debug(f"Skipping file - invalid modality: {dcm.Modality}")

            except Exception as e:
                logger.error(f"Error processing individual file {file}: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"Error in main processing loop: {str(e)}")
    
    logger.info("=== DICOM Series Separation Complete ===")


## Hash Calculation
def calculate_hash(file_path):
    logger.debug(f"Calculating hash for file: {file_path}")
    try:
        hash_md5 = hashlib.sha512()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        hash_value = hash_md5.hexdigest()
        logger.debug(f"Hash calculation complete: {hash_value[:10]}...")
        return hash_value
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {str(e)}")
        raise

## DICOM Metadata Reading
def read_dicom_metadata(dicom_series_path, unprocess_dicom_path, deidentified_dicom_path):
    logger.info(f"Starting DICOM metadata processing for path: {dicom_series_path}")
    try:
        # Read initial DICOM file
        logger.debug(f"Reading DICOM file from: {dicom_series_path}")
        ds = pydicom.dcmread(
                os.path.join(
                    dicom_series_path,
                    os.listdir(dicom_series_path)[0])
            )

        # Create or update DicomUnprocessed record
        logger.debug("Creating/updating DicomUnprocessed record")
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
        logger.info(f"Processing studydate: {processing.studydate}")

        # Check for YAML files
        yaml_files = glob.glob(os.path.join(dicom_series_path, "*.yml"))
        logger.debug(f"Found {len(yaml_files)} YAML files")

        if len(yaml_files) == 1:
            logger.debug("Processing single YAML file")
            yaml_file_path = yaml_files[0]
            yaml_file_hash = calculate_hash(yaml_file_path)

            if ModelYamlInfo.objects.filter(file_hash=yaml_file_hash).exists():
                yaml_file_name = ModelYamlInfo.objects.get(file_hash=yaml_file_hash).yaml_name
                logger.info(f"Matching YAML file found: {yaml_file_name}")
                
                logger.debug(f"Moving directory to: {deidentified_dicom_path}")
                shutil.move(dicom_series_path, deidentified_dicom_path)

                DicomUnprocessed.objects.filter(id=processing.id).update(
                    series_folder_location=deidentified_dicom_path
                )
                
                ProcessingStatus.objects.create(
                    patient_id=DicomUnprocessed.objects.get(id=processing.id),
                    status=f"{yaml_file_name} Template file matched",
                    dicom_move_folder_status="Move to Deidentification Folder",
                )
                logger.info("Successfully processed and moved to deidentification folder")

            else:
                logger.warning("Protocol key does not exist, moving to unprocessed folder")
                shutil.move(dicom_series_path, unprocess_dicom_path)

                ProcessingStatus.objects.create(
                    patient_id=DicomUnprocessed.objects.get(id=processing.id),
                    status="Invalid Template file",
                    dicom_move_folder_status="Move to Unprocessed Folder",
                )

                DicomUnprocessed.objects.filter(id=processing.id).update(
                    series_folder_location=unprocess_dicom_path,
                    unprocessed=True
                )

        elif len(yaml_files) == 0:
            logger.debug("No YAML files found, processing DICOM tags")
            try:
                ds = pydicom.dcmread(
                    os.path.join(dicom_series_path, os.listdir(dicom_series_path)[0])
                )
                
                # Process DICOM tags
                logger.debug("Processing DICOM tags")
                tag_list = []
                for elem in ds:
                    tag_dict = {
                        'tag': str(elem.tag),
                        'tag_name': elem.name.replace(" ", ""),
                        'tag_value': str(elem.value)
                    }
                    tag_list.append(tag_dict)

                # Create and process DataFrames
                logger.debug("Creating and processing DataFrames")
                tag_df = pd.DataFrame(tag_list)
                tag_df["patient_id"] = ds.PatientID

                rule_set_table = Rule.objects.all().values(
                    "rule_set__id","rule_set__rule_set_name", "tag_name__tag_name", "tag_value"
                )
                rule_set_table_df = pd.DataFrame(list(rule_set_table))
                rule_set_table_df["count_rule"] = rule_set_table_df.groupby("rule_set__id")["rule_set__id"].transform("count")
                rule_set_table_df.rename(columns={"tag_name__tag_name": "tag_name", "tag_value": "tag_value"}, inplace=True)

                join_df = pd.merge(tag_df, rule_set_table_df, on=['tag_name','tag_value']).dropna()
                logger.debug(f"Merged DataFrame size: {len(join_df)}")

                match_rule = join_df.groupby(["rule_set__id", "patient_id", "count_rule"]).count().reset_index()
                match_rule = match_rule[["rule_set__id", "patient_id", "count_rule", "rule_set__rule_set_name"]]
                match_rule.rename(columns={"rule_set__rule_set_name": "match_rule"}, inplace=True)
                
                filter_match_rule = match_rule.loc[(match_rule["count_rule"]) == (match_rule["match_rule"])]
                logger.info(f"Found {len(filter_match_rule)} matching rules")

                if len(filter_match_rule) == 1:
                    logger.info("Single rule match found, processing")
                    model_yaml_path = RuleSet.objects.filter(
                        id=filter_match_rule["rule_set__id"].unique()[0]
                    ).values("model_yaml__yaml_path").first()["model_yaml__yaml_path"]

                    model_yaml_name = RuleSet.objects.filter(
                        id=filter_match_rule["rule_set__id"].unique()[0]
                    ).values("model_yaml__yaml_name").first()["model_yaml__yaml_name"]

                    logger.debug(f"Copying YAML file: {model_yaml_path}")
                    shutil.copy2(
                        model_yaml_path,
                        os.path.join(dicom_series_path)
                    )

                    logger.debug(f"Moving directory to: {deidentified_dicom_path}")
                    shutil.move(dicom_series_path, deidentified_dicom_path)

                    ProcessingStatus.objects.create(
                        patient_id=DicomUnprocessed.objects.get(id=processing.id),
                        status=f"{model_yaml_name} Template file Attached",
                        yaml_attach_status="Yaml file attached",
                        dicom_move_folder_status="Move to Deidentification Folder"
                    )

                    DicomUnprocessed.objects.filter(id=processing.id).update(
                        series_folder_location=deidentified_dicom_path)
                    
                elif len(filter_match_rule) > 1:
                    logger.warning("Multiple rule matches found")
                    shutil.move(dicom_series_path, unprocess_dicom_path)

                    multiple_rules = ', '.join(rule_set_table_df["rule_set__rule_set_name"].unique().tolist())
                    logger.info(f"Matched rules: {multiple_rules}")

                    ProcessingStatus.objects.create(
                        patient_id=DicomUnprocessed.objects.get(id=processing.id),
                        status=f"Rule Sets Matched : {multiple_rules}",
                        dicom_move_folder_status="Move to Unprocessed Folder", 
                    )

                    DicomUnprocessed.objects.filter(id=processing.id).update(
                        series_folder_location=unprocess_dicom_path,
                        unprocessed=True
                    )
                else:
                    logger.warning("No matching rules found")
                    shutil.move(dicom_series_path, unprocess_dicom_path)
                    ProcessingStatus.objects.create(
                        patient_id=DicomUnprocessed.objects.get(id=processing.id),
                        status="No Rule Sets Matched",
                        dicom_move_folder_status="Move to Unprocessed Folder", 
                    )

                    DicomUnprocessed.objects.filter(id=processing.id).update(
                        series_folder_location=unprocess_dicom_path,
                        unprocessed=True
                    )

            except Exception as e:
                logger.error(f"Error processing DICOM tags: {str(e)}")
                raise

        else:
            logger.warning(f"Multiple YAML files found ({len(yaml_files)}), moving to unprocessed folder")
            shutil.move(dicom_series_path, unprocess_dicom_path)

            ProcessingStatus.objects.create(
                patient_id=DicomUnprocessed.objects.get(id=processing.id),
                status="Multiple Yaml file in folder",
                dicom_move_folder_status="Move to Unprocessed Folder"
            )

            DicomUnprocessed.objects.filter(id=processing.id).update(
                series_folder_location=unprocess_dicom_path,
                unprocessed=True
            )

    except Exception as e:
        logger.error(f"Error in read_dicom_metadata: {str(e)}")
        raise

    logger.info("Completed DICOM metadata processing")