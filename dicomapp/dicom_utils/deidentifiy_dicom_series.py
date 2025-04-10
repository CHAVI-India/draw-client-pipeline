from dicomapp.models import *
from logging import getLogger
import os
from pathlib import Path
import shutil
from datetime import datetime, timedelta
from django.conf import settings
import pydicom
from deidapp.models import *
from deidapp.dicomutils.deidentify_dicom import deidentify_dicom
import pandas as pd
import glob
import hashlib

logger = getLogger(__name__)

def deidentify_dicom_series(match_result: dict) -> dict:
    """
    Deidentify DICOM files in a directory. This function is called after the series have been matched to a template.
    It will take the series folder paths where the deidentification was successful and will deidentify the DICOM files using the deidentify_dicom function.
    
    Args:
        match_result (dict): Dictionary returned by match_autosegmentation_template containing:
            - status: The status of the operation ('success', 'partial_failure', or 'failure')
            - task_id: The id of the celery task
            - message: The message to be displayed
            - series_folder_paths: Dictionary with keys 'successful' and 'failed' containing lists of paths where series folders were moved
            - deidentification_status: true if the series is ready for deidentification, false otherwise
            - failed_series: List of series IDs that failed to process
            - successful_series: List of series IDs that were processed successfully
    
    Returns:
        dict: Dictionary with the following keys:
            - status (success, partial_failure, or failure)
            - task_id: The id of the celery task
            - message (message to be displayed)
            - series_folder_paths: Dictionary with keys 'successful' and 'failed' containing lists of paths where series folders were moved
            - deidentification_status: true if the series is ready for deidentification, false otherwise
            - failed_series: List of series IDs that failed to process
            - successful_series: List of series IDs that were processed successfully
    """
    try:
        logger.info(f"Starting DICOM deidentification for match result: {match_result}")
        
        # Check if we have any successful series to process
        if not match_result.get("successful_series"):
            logger.warning("No successful series to process from match result")
            return match_result
        
        # Get base directories from settings using os.path
        base_dir = settings.BASE_DIR
        processed_dir = os.path.join(base_dir, "folders", "folder_post_deidentification")
        
        # Create processed directory if it doesn't exist
        os.makedirs(processed_dir, exist_ok=True)
        logger.info(f"Processed directory created at: {processed_dir}")
        
        # Track successful and failed series
        successful_series = []
        failed_series = []
        successful_series_paths = []
        failed_series_paths = []
        
        # Process each successful series from match result
        for series_id in match_result["successful_series"]:
            try:
                # Get the series processing model instance
                try:
                    series_model = DicomSeriesProcessingModel.objects.get(id=series_id)
                    logger.info(f"Series processing model instance: {series_model}")
                    logger.info(f"Series processing model instance processing status: {series_model.processing_status}")
                except Exception as model_error:
                    error_msg = f"Failed to get series model: {str(model_error)}"
                    logger.error(error_msg)
                    failed_series.append(series_id)
                    if series_dir:
                        failed_series_paths.append(series_dir)
                    continue
                
                # Get the series directory from successful paths
                series_dir = None
                logger.info(f"Processing series {series_id}")
                logger.info(f"Available successful paths: {match_result['series_folder_paths']['successful']}")
                
                # Get the corresponding path for this series
                try:
                    if match_result["series_folder_paths"]["successful"]:
                        # Get the index of the current series in successful_series list
                        series_index = match_result["successful_series"].index(series_id)
                        # Get the corresponding path at the same index
                        series_dir = match_result["series_folder_paths"]["successful"][series_index]
                        logger.info(f"Using path for series {series_id}: {series_dir}")
                    else:
                        logger.warning("No successful paths available")
                except Exception as path_error:
                    error_msg = f"Failed to get series directory path: {str(path_error)}"
                    logger.error(error_msg)
                    failed_series.append(series_id)
                    if series_dir:
                        failed_series_paths.append(series_dir)
                    continue
                
                # Check if series is ready for deidentification
                if series_model.processing_status == ProcessingStatusChoices.READY_FOR_DEIDENTIFICATION:
                    try:
                        logger.info(f"Processing series {series_id} at path {series_dir}")
                        logger.info(f"Directory exists: {os.path.exists(series_dir)}")
                        logger.info(f"Directory contents: {os.listdir(series_dir)}")
                        

                        # Call the deidentify_dicom function from deidapp
                        logger.info(f"Calling deidentify_dicom with dicom_dir={series_dir} and processed_dir={processed_dir}")
                        try:
                            result = deidentify_dicom(
                                dicom_dir=series_dir,
                                processed_dir=processed_dir,
                                task_id=match_result["task_id"],
                                dicom_series_processing_id=series_model.id
                            )
                            logger.info(f"Deidentification result: {result}")
                            
                            if result.get("status") == "success" and result.get("deidentified_path"):
                                # Update database but not the series current directory as if the deidentification succeds the folder is deleted.
                                series_model.processing_status = ProcessingStatusChoices.DEIDENTIFIED
                                series_model.series_state = SeriesState.PROCESSING
                                #series_model.series_current_directory = result["deidentified_path"]
                                series_model.save()
                                
                                # Create log entry
                                DicomSeriesProcessingLogModel.objects.create(
                                    task_id=match_result["task_id"],
                                    dicom_series_processing_id=series_model,
                                    processing_status=ProcessingStatusChoices.DEIDENTIFIED,
                                    processing_status_message="Series successfully deidentified"
                                )
                                
                                logger.info(f"Successfully processed series {series_id}")
                                successful_series.append(series_id)
                                successful_series_paths.append(result["deidentified_path"])
                            else:
                                error_msg = result.get("message", "Unknown error during deidentification")
                                # Update database for failure. 
                                series_model.processing_status = ProcessingStatusChoices.DEIDENTIFICATION_FAILED
                                series_model.series_state = SeriesState.FAILED
                                series_model.save()
                                    
                                # Create log entry
                                DicomSeriesProcessingLogModel.objects.create(
                                    task_id=match_result["task_id"],
                                    dicom_series_processing_id=series_model,
                                    processing_status=ProcessingStatusChoices.DEIDENTIFICATION_FAILED,
                                    processing_status_message=f"Deidentification failed: {error_msg}"
                                )
                                
                                logger.error(f"Failed to process series {series_id}: {error_msg}")
                                failed_series.append(series_id)
                                failed_series_paths.append(series_dir)
                        except Exception as deid_error:
                            error_msg = f"Error during deidentification process: {str(deid_error)}"
                            logger.error(error_msg)
                            
                            # Update database for failure
                            series_model.processing_status = ProcessingStatusChoices.DEIDENTIFICATION_FAILED
                            series_model.series_state = SeriesState.FAILED
                            series_model.save()
                            
                            # Create log entry
                            DicomSeriesProcessingLogModel.objects.create(
                                task_id=match_result["task_id"],
                                dicom_series_processing_id=series_model,
                                processing_status=ProcessingStatusChoices.DEIDENTIFICATION_FAILED,
                                processing_status_message=error_msg
                            )
                            
                            failed_series.append(series_id)
                            failed_series_paths.append(series_dir)
                            continue
                    except Exception as deid_error:
                        error_msg = f"Error during deidentification process: {str(deid_error)}"
                        logger.error(error_msg)
                        
                        # Update database for failure
                        series_model.processing_status = ProcessingStatusChoices.DEIDENTIFICATION_FAILED
                        series_model.series_state = SeriesState.FAILED
                        series_model.save()
                        
                        # Create log entry
                        DicomSeriesProcessingLogModel.objects.create(
                            task_id=match_result["task_id"],
                            dicom_series_processing_id=series_model,
                            processing_status=ProcessingStatusChoices.DEIDENTIFICATION_FAILED,
                            processing_status_message=error_msg
                        )
                        
                        failed_series.append(series_id)
                        failed_series_paths.append(series_dir)
                        continue
                else:
                    error_msg = f"Series {series_id} is not ready for deidentification. Current status: {series_model.processing_status}"
                    logger.error(error_msg)
                    failed_series.append(series_id)
                    if series_dir:
                        failed_series_paths.append(series_dir)
                    
                    # Update database status
                    series_model.processing_status = ProcessingStatusChoices.ERROR
                    series_model.series_state = SeriesState.FAILED
                    series_model.save()
                    
                    # Create log entry
                    DicomSeriesProcessingLogModel.objects.create(
                        task_id=match_result["task_id"],
                        dicom_series_processing_id=series_model,
                        processing_status=ProcessingStatusChoices.ERROR,
                        processing_status_message=error_msg
                    )
                    continue
                
            except Exception as e:
                error_msg = f"Unexpected error processing series {series_id}: {str(e)}"
                logger.error(error_msg)
                
                # Update database status
                if 'series_model' in locals():
                    series_model.processing_status = ProcessingStatusChoices.ERROR
                    series_model.series_state = SeriesState.FAILED
                    series_model.save()
                    
                    # Create log entry
                    DicomSeriesProcessingLogModel.objects.create(
                        task_id=match_result["task_id"],
                        dicom_series_processing_id=series_model,
                        processing_status=ProcessingStatusChoices.ERROR,
                        processing_status_message=error_msg
                    )
                
                failed_series.append(series_id)
                failed_series_paths.append(series_dir)
                continue
        
        # Add any failed series from match result to our failed series list
        failed_series.extend(match_result.get("failed_series", []))
        failed_series_paths.extend(match_result.get("series_folder_paths", {}).get("failed", []))
        
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
            "task_id": match_result["task_id"]
        }
        
    except Exception as e:
        logger.error(f"Error in deidentify_dicom: {str(e)}")
        return {
            "status": "failure",
            "message": f"Error processing series: {str(e)}",
            "series_folder_paths": {
                "successful": [],
                "failed": []
            },
            "deidentification_status": False,
            "failed_series": match_result.get("successful_series", []),
            "successful_series": [],
            "task_id": match_result.get("task_id")
        }

        
        
