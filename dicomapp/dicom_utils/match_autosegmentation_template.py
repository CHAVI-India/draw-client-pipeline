from dicomapp.models import *
from logging import getLogger
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from django.conf import settings
import pydicom
from dicom_handler.models import ModelYamlInfo, Rule, RuleSet
import pandas as pd
import glob
import hashlib

logger = getLogger(__name__)

def calculate_hash(file_path):
    """Calculate SHA-512 hash of a file."""
    try:
        hash_md5 = hashlib.sha512()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {str(e)}")
        raise

def match_autosegmentation_template(input_data: dict) -> dict:
    """
    This function will match a autosegmentation template to the series. It will update the database entries based on the series_processing_ids returned by the series_preparation function.
    The folder moved will be the folder where dicom images of a series are present. Each folder is an unique series.

    It will read the DICOM metadata of the dicom files in the series folder. It will skip non dicom files if any in the folder.
    If a match is found it will read the dicom metadata and see if a single autosegmentation template can be matched. If one is matched it will move the series folder as a whole to a new folder called "folder_for_deidentification" insides folders directory (relative to the Base directory). 
    It will update the DicomSeriesProcessingModel table with the FK relationship to the ModelYamlInfo table.
    Additionally, it will:
    1. Update the processing_status to ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION
    2. Update the series_state to SeriesState.PROCESSING
    3. Save the task_id of the celery task in the DicomSeriesProcessingModel table.
    4. It will update the field called series_current_directory to the folder location where the series folder is now located.
    4. Create a log entry in the DicomSeriesProcessingLogModel table with a summary of the series processing.
    5. Update the DicomSeriesProcessingModel table with the processing_status to ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION

    If not it will move the series folder as a whole to a folder called 'unprocessed_folder' inside the folders directory (relative to the Base directory). The databse updates will be handled differently based on the number of templates matched. 

    If multiple templates are matched it will update the processing_status to ProcessingStatusChoices.MULTIPLE_TEMPLATES_MATCHED
    If no templates are matched it will update the processing_status to ProcessingStatusChoices.NO_TEMPLATE_FOUND
    It will also update the DicomSeriesProcessingLogModel table with the corresponding processing_status and processing_status_message. The current series folder path will be updated to the unprocessed_folder path where the series folder is now located.

    Args:
        input_data (dict): A dictionary containing:
            - status: The status of the operation ('success', 'partial_failure', or 'failure')
            - task_id: The id of the celery task
            - message: The message to be displayed
            - separated_series_path_folders: List of paths where series folders were separated
            - series_processing_ids: List of UUIDs of created DicomSeriesProcessingModel entries

    Returns:
        dict: Dictionary with the following keys:
            - status (success, partial_failure, or failure)
            - message (message to be displayed)
            - series_folder_paths: Dictionary with keys 'successful' and 'failed' containing lists of paths where series folders were moved
            - deidentification_status: true if the series is ready for deidentification, false otherwise
            - failed_series: List of series IDs that failed to process
            - successful_series: List of series IDs that were processed successfully
            - task_id: The id of the celery task
    """
    logger.info("Starting match_autosegmentation_template function")
    
    try:
        # Get base directories from settings using os.path
        base_dir = settings.BASE_DIR
        deidentification_folder = os.path.join(base_dir, "folders", "folder_for_deidentification")
        unprocessed_folder = os.path.join(base_dir, "folders", "unprocessed_folder")
        
        # Create directories if they don't exist
        os.makedirs(deidentification_folder, exist_ok=True)
        os.makedirs(unprocessed_folder, exist_ok=True)
        
        # Get input data and convert paths to strings
        task_id = input_data.get('task_id')
        if not task_id:
            logger.error("Missing required task_id in input data")
            return {
                "status": "failure",
                "message": "Missing required task_id in input data",
                "series_folder_paths": {
                    "successful": [],
                    "failed": []
                },
                "deidentification_status": False,
                "failed_series": [],
                "successful_series": [],
                "task_id": None
            }
            
        series_processing_ids = input_data.get('series_processing_ids', [])
        separated_series_path_folders = [str(path) for path in input_data.get('separated_series_path_folders', [])]
        
        if not series_processing_ids or not separated_series_path_folders:
            logger.error("Missing required input data")
            return {
                "status": "failure",
                "message": "Missing required input data",
                "series_folder_paths": {
                    "successful": [],
                    "failed": []
                },
                "deidentification_status": False,
                "failed_series": [],
                "successful_series": [],
                "task_id": task_id
            }
        
        # Track successful and failed series
        successful_series = []
        failed_series = []
        successful_series_paths = []
        failed_series_paths = []
        
        # Process each series
        for series_id, series_path in zip(series_processing_ids, separated_series_path_folders):
            try:
                logger.info(f"Processing series {series_id} at path {series_path}")
                
                # Get the series processing model instance
                series_model = DicomSeriesProcessingModel.objects.get(id=series_id)
                
                # Check for YAML files in the series folder
                yaml_files = glob.glob(os.path.join(series_path, "*.yml")) + glob.glob(os.path.join(series_path, "*.yaml"))
                
                if len(yaml_files) == 1:
                    # Single YAML file found
                    yaml_file_path = yaml_files[0]
                    yaml_file_hash = calculate_hash(yaml_file_path)
                    
                    if ModelYamlInfo.objects.filter(file_hash=yaml_file_hash).exists():
                        # Valid template found
                        template = ModelYamlInfo.objects.get(file_hash=yaml_file_hash)
                        dest_dir = os.path.join(deidentification_folder, os.path.basename(series_path))
                        
                        # Move series folder
                        if os.path.exists(dest_dir):
                            shutil.rmtree(dest_dir)
                        shutil.move(series_path, dest_dir)
                        
                        # Update database
                        series_model.template_file = template
                        series_model.processing_status = ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION
                        series_model.series_state = SeriesState.PROCESSING
                        series_model.series_current_directory = dest_dir
                        series_model.task_id = task_id
                        series_model.save()
                        
                        # Create log entry
                        DicomSeriesProcessingLogModel.objects.create(
                            task_id=task_id,
                            dicom_series_processing_id=series_model,
                            processing_status=ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION,
                            processing_status_message=f"Template {template.yaml_name} matched successfully"
                        )
                        
                        logger.info(f"Successfully processed series {series_id} with template {template.yaml_name}")
                        successful_series.append(series_id)
                        successful_series_paths.append(dest_dir)
                        
                    else:
                        # Invalid template
                        dest_dir = os.path.join(unprocessed_folder, os.path.basename(series_path))
                        if os.path.exists(dest_dir):
                            shutil.rmtree(dest_dir)
                        shutil.move(series_path, dest_dir)
                        
                        series_model.processing_status = ProcessingStatusChoices.NO_TEMPLATE_FOUND
                        series_model.series_state = SeriesState.UNPROCESSED
                        series_model.series_current_directory = dest_dir
                        series_model.task_id = task_id
                        series_model.save()
                        
                        DicomSeriesProcessingLogModel.objects.create(
                            task_id=task_id,
                            dicom_series_processing_id=series_model,
                            processing_status=ProcessingStatusChoices.NO_TEMPLATE_FOUND,
                            processing_status_message="Invalid template file found"
                        )
                        
                        logger.warning(f"Invalid template found for series {series_id}")
                        failed_series.append(series_id)
                        failed_series_paths.append(dest_dir)
                
                elif len(yaml_files) > 1:
                    # Multiple YAML files found
                    dest_dir = os.path.join(unprocessed_folder, os.path.basename(series_path))
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)
                    shutil.move(series_path, dest_dir)
                    
                    series_model.processing_status = ProcessingStatusChoices.MULTIPLE_TEMPLATES_FOUND
                    series_model.series_state = SeriesState.UNPROCESSED
                    series_model.series_current_directory = dest_dir
                    series_model.task_id = task_id
                    series_model.save()
                    
                    DicomSeriesProcessingLogModel.objects.create(
                        task_id=task_id,
                        dicom_series_processing_id=series_model,
                        processing_status=ProcessingStatusChoices.MULTIPLE_TEMPLATES_FOUND,
                        processing_status_message="Multiple template files found"
                    )
                    
                    logger.warning(f"Multiple templates found for series {series_id}")
                    failed_series.append(series_id)
                    failed_series_paths.append(dest_dir)
                
                else:
                    # No YAML files found, try to match based on DICOM tags
                    try:
                        # Read first file irrespective of the file format
                        dicom_files = glob.glob(os.path.join(series_path, "*"))
                        logger.info(f"Found {len(dicom_files)} files in series {series_id}")
                        if not dicom_files:
                            raise ValueError("No DICOM files found in series")

                        # Read files one by one till the first valid dicom file is read.
                        for file in dicom_files:
                            try: 
                                ds = pydicom.dcmread(file)
                                logger.info(f"Successfully read DICOM file with UIDs: PatientID={ds.PatientID}, StudyInstanceUID={ds.StudyInstanceUID}, SeriesInstanceUID={ds.SeriesInstanceUID}")
                                break
                            except Exception as e:
                                logger.warning(f"Error reading DICOM file {file}: {str(e)}")
                                continue
                        
                        # Process DICOM tags
                        tag_list = []
                        for elem in ds:
                            # Skip PixelData tag as it's not needed for template matching
                            if elem.tag == (0x7FE0, 0x0010):  # PixelData tag
                                continue
                            tag_dict = {
                                'tag': str(elem.tag),
                                'tag_name': elem.name.replace(" ", ""),
                                'tag_value': str(elem.value)
                            }
                            tag_list.append(tag_dict)
                        logger.info(f"Tag dictionary: {tag_list}")
                        # Create DataFrame and match rules
                        tag_df = pd.DataFrame(tag_list)
                        logger.info(f"Tag DataFrame: {tag_df}")
                        tag_df["patient_id"] = ds.PatientID
                        logger.info(f"Tag DataFrame with patient ID: {tag_df}")
                        rule_set_table = Rule.objects.all().values(
                            "rule_set__id", "rule_set__rule_set_name", 
                            "tag_name__tag_name", "tag_value"
                        )
                        logger.info(f"Rule set table: {rule_set_table}")
                        rule_set_table_df = pd.DataFrame(list(rule_set_table))
                        logger.info(f"Rule set table DataFrame: {rule_set_table_df}")
                        rule_set_table_df["count_rule"] = rule_set_table_df.groupby("rule_set__id")["rule_set__id"].transform("count")
                        logger.info(f"Rule set table DataFrame with count_rule: {rule_set_table_df}")
                        rule_set_table_df.rename(columns={
                            "tag_name__tag_name": "tag_name", 
                            "tag_value": "tag_value"
                        }, inplace=True)
                        logger.info(f"Rule set table DataFrame with renamed columns: {rule_set_table_df}")
                        join_df = pd.merge(tag_df, rule_set_table_df, on=['tag_name', 'tag_value']).dropna()
                        logger.info(f"Join DataFrame: {join_df}")
                        match_rule = join_df.groupby(["rule_set__id", "patient_id", "count_rule"]).count().reset_index()
                        logger.info(f"Match rule DataFrame: {match_rule}")
                        match_rule = match_rule[["rule_set__id", "patient_id", "count_rule", "rule_set__rule_set_name"]]
                        match_rule.rename(columns={"rule_set__rule_set_name": "match_rule"}, inplace=True)
                        logger.info(f"Match rule DataFrame with renamed columns: {match_rule}")
                        filter_match_rule = match_rule.loc[(match_rule["count_rule"]) == (match_rule["match_rule"])]
                        logger.info(f"Filter match rule DataFrame: {filter_match_rule}")
                        if len(filter_match_rule) == 1:
                            # Single rule match found
                            rule_set_id = filter_match_rule["rule_set__id"].unique()[0]
                            rule_set = RuleSet.objects.get(id=rule_set_id)
                            
                            # Copy template and move folder
                            template_path = rule_set.model_yaml.yaml_path
                            shutil.copyfile(template_path, series_path)
                            
                            dest_dir = os.path.join(deidentification_folder, os.path.basename(series_path))
                            if os.path.exists(dest_dir):
                                shutil.rmtree(dest_dir)
                            shutil.move(series_path, dest_dir)
                            logger.info(f"Successfully moved series {series_id} to {dest_dir}")
                            # Update database
                            series_model.template_file = rule_set.model_yaml
                            series_model.processing_status = ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION
                            series_model.series_state = SeriesState.PROCESSING
                            series_model.series_current_directory = dest_dir
                            series_model.task_id = task_id
                            series_model.save()
                            logger.info(f"Successfully updated database for series {series_id}")

                            DicomSeriesProcessingLogModel.objects.create(
                                task_id=task_id,
                                dicom_series_processing_id=series_model,
                                processing_status=ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION,
                                processing_status_message=f"Template {rule_set.model_yaml.yaml_name} matched based on rules"
                            )
                            logger.info(f"Successfully created log entry for series {series_id}")
                            
                            logger.info(f"Successfully matched template for series {series_id} based on ruleset {rule_set.rule_set_name}")
                            successful_series.append(series_id)
                            successful_series_paths.append(dest_dir)
                            
                        elif len(filter_match_rule) > 1:
                            # Multiple rule matches
                            dest_dir = os.path.join(unprocessed_folder, os.path.basename(series_path))
                            if os.path.exists(dest_dir):
                                shutil.rmtree(dest_dir)
                            shutil.move(series_path, dest_dir)
                            logger.info(f"Successfully moved series {series_id} to {dest_dir}")
                            series_model.processing_status = ProcessingStatusChoices.MULTIPLE_TEMPLATES_MATCHED
                            series_model.series_state = SeriesState.UNPROCESSED
                            series_model.series_current_directory = dest_dir
                            series_model.task_id = task_id
                            series_model.save()
                            logger.info(f"Successfully updated database for series {series_id}")
                            multiple_rules = ', '.join(filter_match_rule["match_rule"].unique().tolist())
                            DicomSeriesProcessingLogModel.objects.create(
                                task_id=task_id,
                                dicom_series_processing_id=series_model,
                                processing_status=ProcessingStatusChoices.MULTIPLE_TEMPLATES_MATCHED,
                                processing_status_message=f"Multiple rule sets matched: {multiple_rules}"
                            )
                            logger.info(f"Successfully created log entry for series {series_id}")
                            
                            logger.warning(f"Multiple rule sets matched for series {series_id}")
                            failed_series.append(series_id)
                            failed_series_paths.append(dest_dir)
                            
                        else:
                            # No rule matches
                            dest_dir = os.path.join(unprocessed_folder, os.path.basename(series_path))
                            if os.path.exists(dest_dir):
                                shutil.rmtree(dest_dir)
                            shutil.move(series_path, dest_dir)
                            logger.info(f"Successfully moved series {series_id} to {dest_dir}")
                            series_model.processing_status = ProcessingStatusChoices.NO_TEMPLATE_FOUND
                            series_model.series_state = SeriesState.UNPROCESSED
                            series_model.series_current_directory = dest_dir
                            series_model.task_id = task_id
                            series_model.save()
                            logger.info(f"Successfully updated database for series {series_id}")
                            DicomSeriesProcessingLogModel.objects.create(
                                task_id=task_id,
                                dicom_series_processing_id=series_model,
                                processing_status=ProcessingStatusChoices.NO_TEMPLATE_FOUND,
                                processing_status_message="No matching rule sets found"
                            )
                            logger.info(f"Successfully created log entry for series {series_id}")
                            
                            logger.warning(f"No rule sets matched for series {series_id}")
                            failed_series.append(series_id)
                            failed_series_paths.append(dest_dir)
                            
                    except Exception as e:
                        error_msg = f"Error processing DICOM tags for series {series_id}: {str(e)}"
                        logger.error(error_msg)
                        
                        # Update database status
                        series_model.processing_status = ProcessingStatusChoices.ERROR
                        series_model.series_state = SeriesState.FAILED
                        series_model.series_current_directory = dest_dir
                        series_model.task_id = task_id
                        series_model.save()
                        logger.info(f"Successfully updated database for series {series_id}")
                        # Create log entry
                        DicomSeriesProcessingLogModel.objects.create(
                            task_id=task_id,
                            dicom_series_processing_id=series_model,
                            processing_status=ProcessingStatusChoices.ERROR,
                            processing_status_message=error_msg
                        )
                        logger.info(f"Successfully created log entry for series {series_id}")
                        
                        failed_series.append(series_id)
                        failed_series_paths.append(dest_dir)
                        continue
                
            except Exception as e:
                error_msg = f"Error processing series {series_id}: {str(e)}"
                logger.error(error_msg)
                
                # Update database status
                series_model.processing_status = ProcessingStatusChoices.ERROR
                series_model.series_state = SeriesState.FAILED
                series_model.series_current_directory = dest_dir
                series_model.task_id = task_id
                series_model.save()
                
                # Create log entry
                DicomSeriesProcessingLogModel.objects.create(
                    task_id=task_id,
                    dicom_series_processing_id=series_model,
                    processing_status=ProcessingStatusChoices.ERROR,
                    processing_status_message=error_msg
                )
                
                failed_series.append(series_id)
                failed_series_paths.append(dest_dir)
                continue
        
        logger.info("Completed match_autosegmentation_template function")
        
        # Determine overall status
        if not failed_series:
            status = "success"
            message = "Successfully processed all series"
        elif not successful_series:
            status = "failure"
            message = "Failed to process all series"
        else:
            status = "partial_failure"
            message = f"Successfully processed {len(successful_series)} series, {len(failed_series)} series failed"
        
        return {
            "status": status,
            "message": message,
            "series_folder_paths": {
                "successful": successful_series_paths,
                "failed": failed_series_paths
            },
            "deidentification_status": bool(successful_series),
            "failed_series": failed_series,
            "successful_series": successful_series,
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Error in match_autosegmentation_template: {str(e)}")
        return {
            "status": "failure",
            "message": f"Error processing series: {str(e)}",
            "series_folder_paths": {
                "successful": [],
                "failed": []
            },
            "deidentification_status": False,
            "failed_series": series_processing_ids,
            "successful_series": [],
            "task_id": task_id
        }
