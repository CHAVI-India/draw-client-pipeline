import os
import shutil
import logging
from typing import Optional, List, Dict, Any
from django.db.models import QuerySet
from dicom_handler.models import *
from dicomapp.models import *
from django.utils import timezone
from django.conf import settings
from celery import chain
from django.contrib import messages
from dicomapp.tasks import deidentify_dicom_series_task, send_dicom_to_remote_server_task

logger = logging.getLogger(__name__)

def delete_yml_in_folder(folder_path: str) -> bool:
    """
    Searches for and deletes all yaml/yml files in the specified folder and its subdirectories.

    Args:
        folder_path (str): The absolute path to the folder to search for yaml/yml files.

    Returns:
        bool: True if all files were successfully deleted, False if any error occurred.

    Raises:
        ValueError: If folder_path is None or empty.
    """
    if not folder_path:
        raise ValueError("folder_path cannot be None or empty")
    
    try:
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.endswith('.yml') or file.endswith('.yaml'):
                    file_path = os.path.join(root, file)
                    os.remove(file_path)
                    logger.info(f"Deleted yaml file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error deleting yaml files in {folder_path}: {str(e)}")
        return False



def send_dicom_for_processing_action(modeladmin, request, queryset: QuerySet) -> None:
    """
    Admin action to send DICOM files for processing. This function:
    1. Validates the processing status of selected series : The valid statues are:
        - SERIES_SEPARATED ( here the series have been seperated but the file was not processed further)
        - TEMPLATE_NOT_MATCHED (autosegmentation template was not matched)
        - MULTIPLE_TEMPLATES_MATCHED (multiple autosegmentation templates were matched)
        - MULTIPLE_TEMPLATES_FOUND (multiple autosegmentation templates were found)
        - NO_TEMPLATE_FOUND (no autosegmentation template was found)
        - READY_FOR_DEIDENTIFICATION (the series is ready for deidentification but has become stuck.)
        - RTSTRUCT_EXPORTED (the rtstruct file has been exported. This special condition to allow manual processing of a successfully processed series).
        - ERROR (an error occurred)
        
    2. Verifies series folder existence
    3. Cleans up existing yaml files
    4. Copies new template yaml files
    5. Triggers the processing chain of celery tasks

    Args:
        modeladmin: The ModelAdmin instance
        request: The current request
        queryset: QuerySet of DicomSeriesProcessingModel instances to process
    """
    # Define valid processing statuses
    logger.info(f"Starting send_dicom_for_processing_action")
    valid_statuses = [
        'SERIES_SEPARATED',
        'TEMPLATE_NOT_MATCHED',
        'MULTIPLE_TEMPLATES_MATCHED',
        'MULTIPLE_TEMPLATES_FOUND',
        'NO_TEMPLATE_FOUND',
        'READY_FOR_DEIDENTIFICATION',
        'RTSTRUCT_EXPORTED', 
        'ERROR'
    ]

    successful_series = []
    failed_series = []
    error_messages = []

    for series in queryset:
        try:
            # Check processing status
            if not series.processing_status or series.processing_status not in valid_statuses:
                error_messages.append(f"Series {series.id}: Invalid processing status {series.processing_status}")
                failed_series.append(series.id)
                continue

            logger.info(f"Series {series.id} has valid processing status {series.processing_status}")

            # Verify series folder exists
            if not series.series_current_directory or not os.path.exists(series.series_current_directory):
                error_messages.append(f"Series {series.id}: Series folder not found at {series.series_current_directory}")
                failed_series.append(series.id)
                continue

            logger.info(f"Series {series.id} has valid series folder {series.series_current_directory}")

            # Delete existing yaml files
            if not delete_yml_in_folder(series.series_current_directory):
                error_messages.append(f"Series {series.id}: Failed to delete existing yaml files")
                failed_series.append(series.id)
                continue

            logger.info(f"Series {series.id} has deleted existing yaml files")

            # Get value of the template file from the selected series
            template_file = series.template_file
            logger.info(f"Series {series.id} has template file {template_file}")

            # Get the path of the template file from the ModelYamlInfo model
            template_file_path = template_file.yaml_path
            logger.info(f"Series {series.id} has template file path {template_file_path}")

            # Check if the file exists at the path
            if not os.path.exists(template_file_path):
                error_messages.append(f"Series {series.id}: Template file not found at {template_file_path}")
                failed_series.append(series.id)
                continue

            logger.info(f"Series {series.id} has template file {template_file_path}")

            # Copy the template file to the series folder
            shutil.copy(template_file_path, series.series_current_directory)

            logger.info(f"Series {series.id} has copied template yaml file")

            # Change the values of the DicomSeriesProcessing model
            series.processing_status = 'READY_FOR_DEIDENTIFICATION'
            series.status = 'PROCESSING'
            series.save()
            logger.info(f"Series {series.id} has updated processing status to TEMPLATE_FILE_COPIED")

            # Prepare task input
            task_input = {
                'status': 'success',
                'message': 'Series folder found and template file copied to series folder',
                'series_folder_paths': {
                    'successful': [series.series_current_directory],
                    'failed': []
                },
                'deidentification_status': True,
                'failed_series': [],
                'successful_series': [series.id],
                'task_id': None
            }

            logger.info(f"Series {series.id} has prepared task input {task_input}")

            # Create celery task chain
            task_chain = chain(
                deidentify_dicom_series_task.s(task_input),
                send_dicom_to_remote_server_task.s()
            )

            logger.info(f"Series {series.id} has created celery task chain {task_chain}")

            # Execute the chain
            result = task_chain.apply_async()
            logger.info(f"Series {series.id} has executed celery task chain {result}")
            if result and hasattr(result, 'id'):
                logger.info(f"Started processing chain for series {series.id} with task ID {result.id}")
            else:
                logger.warning(f"Task chain started for series {series.id} but no task ID was returned")
            
            successful_series.append(series.id)

        except Exception as e:
            logger.error(f"Error processing series {series.id}: {str(e)}")
            error_messages.append(f"Series {series.id}: Unexpected error - {str(e)}")
            failed_series.append(series.id)
            logger.info(f"Series {series.id} has failed to process")
    # Display results to user
    if successful_series:
        messages.success(request, f"Successfully started processing for {len(successful_series)} series: {successful_series}")
    if failed_series:
        messages.error(request, f"Failed to process {len(failed_series)} series: {failed_series}")
        for error in error_messages:
            messages.error(request, error)

    