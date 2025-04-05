import os
import shutil
import pydicom
from datetime import datetime
from dicomapp.models import DicomSeriesProcessingModel, DicomSeriesProcessingLogModel, CopyDicomTaskModel, ProcessingStatusChoices, SeriesState
from deidapp.models import Patient, DicomStudy, DicomSeries, DicomInstance, RTStructFile
import logging
from django.conf import settings

# Get logger
logger = logging.getLogger(__name__)


def export_rtstruct(dict):
    """
    This function is part of a Celery task chain that processes RTSTRUCT files.
    It runs after the reidentify_rtstruct_file function and exports the reidentified RTSTRUCT files
    to their final destination in the datastore.

    Args:
        dict: Dictionary from reidentify_rtstruct_file containing:
            - processed_count: number of successfully processed files
            - error_count: number of files that failed processing
            - processed_paths: list of paths to successfully processed and reidentified RTSTRUCT files
            - rtstruct_file_ids: list of primary keys of the RTStructFile records that were successfully processed

    The function will loop through the rtstruct_file_ids and lookup the record from the RTStructFile table using this primary key. 
    It will also keep the corresponding processed_path from the processed_paths list.
    It will lookup the table called DicomSeries by matching the dicom_series field with the series_instance_uid field in the DicomSeries table.
    It will get the dicom_series_processing_id value from the DicomSeries table.
    It will then match this id value to the primary key value the id on the DicomSeriesProcessingModel table in the dicomapp (note that this is not a FK reference)
    After that it will get the value of the corresponding primary key of the CopyDicomTaskModel table from the DicomSeriesProcessingModel table.
    It will then get the value of the source_directory field from the CopyDicomTaskModel table.
    It will then move the file to the source_directory field value.
    After that it will update the following models:
    1. CopyDicomTaskModel:
        - It will update the source_directory_modification_date field to the current date time.
    2. DicomSeriesProcessingModel:
        - It will update the processing_status field to 'RTSTRUCT_EXPORTED'
        - It will update the series_state field to 'COMPLETE'
    3. DicomSeriesProcessingLogModel:
        - It will create a new record with the processing_status 'RTSTRUCT_EXPORTED'
        - It will create a new record with the processing_status_message "RT structure set file exported to the data store with the path {source_directory}"

    Returns:
        dict: Dictionary containing:
            - processed_count: number of successfully exported files
            - error_count: number of files that failed export
            - processed_paths: list of paths to successfully exported RTSTRUCT files
            - rtstruct_file_ids: list of primary keys of the RTStructFile records that were successfully exported
    """
    logger.info("Starting RTSTRUCT export process")

    # Validate input dictionary
    required_keys = ['processed_count', 'error_count', 'processed_paths', 'rtstruct_file_ids']
    if not all(key in dict for key in required_keys):
        logger.error(f"Invalid input dictionary. Missing required keys: {[key for key in required_keys if key not in dict]}")
        return {
            'processed_count': 0,
            'error_count': 1,
            'processed_paths': [],
            'rtstruct_file_ids': []
        }

    try:
        # Initialize results
        processed_count = 0
        error_count = 0
        processed_paths = []
        rtstruct_file_ids = []

        # Get the list of RTStructFile IDs and processed paths from the input
        rtstruct_file_ids = dict.get('rtstruct_file_ids', [])
        processed_paths = dict.get('processed_paths', [])

        # Validate that we have matching lists
        if len(rtstruct_file_ids) != len(processed_paths):
            logger.error(f"Mismatch between rtstruct_file_ids ({len(rtstruct_file_ids)}) and processed_paths ({len(processed_paths)})")
            return {
                'processed_count': 0,
                'error_count': 1,
                'processed_paths': [],
                'rtstruct_file_ids': []
            }

        # Loop through the RTStructFile IDs
        for rtstruct_file_id, processed_path in zip(rtstruct_file_ids, processed_paths):
            try:
                # Get the RTStructFile record
                rtstruct_file = RTStructFile.objects.get(id=rtstruct_file_id)
                logger.info(f"Exporting RTSTRUCT file: {rtstruct_file.series_instance_uid}")

                # Validate that the processed path exists
                if not os.path.exists(processed_path):
                    raise FileNotFoundError(f"Processed file not found at path: {processed_path}")

                logger.info(f"Processed path: {processed_path}")
                # Get the DicomSeries record
                try:
                    dicom_series = DicomSeries.objects.get(series_instance_uid=rtstruct_file.dicom_series)
                    logger.info(f"Dicom series: {dicom_series.series_instance_uid}")
                except DicomSeries.DoesNotExist:
                    raise ValueError(f"DicomSeries not found for series_instance_uid: {rtstruct_file.dicom_series}")

                # Get the dicom_series_processing_id value
                dicom_series_processing_id = dicom_series.dicom_series_processing_id
                logger.info(f"Dicom series processing id: {dicom_series_processing_id}")

                # Get the corresponding DicomSeriesProcessingModel record
                try:
                    dicom_series_processing_model = DicomSeriesProcessingModel.objects.get(id=dicom_series_processing_id)
                    logger.info(f"Dicom series processing model: {dicom_series_processing_model.id}")
                except DicomSeriesProcessingModel.DoesNotExist:
                    raise ValueError(f"DicomSeriesProcessingModel not found for id: {dicom_series_processing_id}")

                # Get the corresponding CopyDicomTaskModel record
                try:
                    copy_dicom_task = CopyDicomTaskModel.objects.get(id=dicom_series_processing_model.copy_dicom_task_id)
                    logger.info(f"Copy dicom task: {copy_dicom_task.id}")
                except CopyDicomTaskModel.DoesNotExist:
                    raise ValueError(f"CopyDicomTaskModel not found for id: {dicom_series_processing_model.copy_dicom_task_id}")

                # Get the source_directory value
                source_directory = copy_dicom_task.source_directory
                if not source_directory:
                    raise ValueError("source_directory is empty in CopyDicomTaskModel")

                # Move the file to the source_directory
                try:
                    shutil.move(processed_path, source_directory)
                    logger.info(f"File moved to: {source_directory}")
                except Exception as move_error:
                    raise RuntimeError(f"Failed to move file: {str(move_error)}")

                # Update the CopyDicomTaskModel record
                try:
                    copy_dicom_task.source_directory_modification_date = datetime.now()
                    copy_dicom_task.save()
                    logger.info(f"Copy dicom task updated")
                except Exception as save_error:
                    raise RuntimeError(f"Failed to update CopyDicomTaskModel: {str(save_error)}")

                # Update the DicomSeriesProcessingModel record
                try:
                    dicom_series_processing_model.processing_status = ProcessingStatusChoices.RTSTRUCT_EXPORTED
                    dicom_series_processing_model.series_state = SeriesState.COMPLETE
                    dicom_series_processing_model.save()
                    logger.info(f"Dicom series processing model updated {dicom_series_processing_model.id} - {dicom_series_processing_model.processing_status} - {dicom_series_processing_model.series_state}")
                except Exception as save_error:
                    raise RuntimeError(f"Failed to update DicomSeriesProcessingModel: {str(save_error)}")

                # Create a new DicomSeriesProcessingLogModel record
                try:
                    dicom_series_processing_log = DicomSeriesProcessingLogModel.objects.create(
                        dicom_series_processing_id=dicom_series_processing_model,
                        processing_status=ProcessingStatusChoices.RTSTRUCT_EXPORTED,
                        processing_status_message=f"RT structure set file exported to the data store with the path {source_directory}"
                    )
                    logger.info(f"Dicom series processing log created {dicom_series_processing_log.id} - {dicom_series_processing_log.processing_status} - {dicom_series_processing_log.processing_status_message}")
                except Exception as create_error:
                    raise RuntimeError(f"Failed to create DicomSeriesProcessingLogModel: {str(create_error)}")

                # Increment the processed_count and add to successful lists
                processed_count += 1
                processed_paths.append(processed_path)
                rtstruct_file_ids.append(rtstruct_file_id)

            except Exception as e:
                logger.error(f"Error exporting RTSTRUCT file {rtstruct_file_id}: {str(e)}", exc_info=True)
                error_count += 1
                # Remove the failed path from processed_paths if it exists
                if processed_path in processed_paths:
                    processed_paths.remove(processed_path)
                if rtstruct_file_id in rtstruct_file_ids:
                    rtstruct_file_ids.remove(rtstruct_file_id)

        logger.info(f"Completed RTSTRUCT export process. Processed: {processed_count}, Errors: {error_count}")
        return {
            'processed_count': processed_count,
            'error_count': error_count,
            'processed_paths': processed_paths,
            'rtstruct_file_ids': rtstruct_file_ids
        }

    except Exception as e:
        logger.error(f"Error in export_rtstruct function: {str(e)}", exc_info=True)
        return {
            'processed_count': 0,
            'error_count': 1,
            'processed_paths': [],
            'rtstruct_file_ids': []
        }

            


