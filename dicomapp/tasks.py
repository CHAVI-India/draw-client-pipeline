from celery import shared_task, chain
from logging import getLogger
from dicomapp.models import *
from django.conf import settings
from dicom_handler.models import DicomPathConfig
from dicomapp.dicom_utils.copy_dicom import copy_dicom
from dicomapp.dicom_utils.series_preparation import series_preparation
from dicomapp.dicom_utils.match_autosegmentation_template import match_autosegmentation_template
from dicomapp.dicom_utils.deidentifiy_dicom_series import deidentify_dicom_series
from dicomapp.dicom_utils.send_dicom_to_remote_server import send_dicom_to_remote_server
from dicomapp.dicom_utils.poll_remote_server import poll_pending_transfers
from dicomapp.dicom_utils.reidentify_and_export_rtstruct_file import reidentify_rtstruct_file_and_export_to_datastore
from dicomapp.dicom_utils.export_rtstruct import export_rtstruct
from dicomapp.dicom_utils.notify_remote_server import notify_completed_transfers

logger = getLogger(__name__)

## DICOM Export Tasks

@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Export - Copy DICOM files to datastore")
def copy_dicom_task(self, datastore_path, target_path=None, task_id=None):
    """
    This task will copy the DICOM files from the datastore path to the target path.
    It will return a dictionary with the following keys:
        - status (success or failure)
        - message (message to be displayed)
        - folder_path (path to the folder inside the target directory where the dicom files are present)
        - copy_dicom_task_id (UUID of the CopyDicomTaskModel instance)
    """
    try:
        # Get the DicomPathConfig instance
        path_config = DicomPathConfig.get_instance()
        # Get a safe path using the get_safe_path method
        safe_path = path_config.get_safe_path()
        if safe_path is None:
            raise ValueError("No valid datastore path configured")
            
        copy_dicom_task_results = copy_dicom(
            datastore_path=str(safe_path),
            target_path=str(target_path) if target_path else None,
            task_id=task_id or self.request.id
        )
        logger.info(f"Copy dicom task results: {copy_dicom_task_results}")
        return copy_dicom_task_results
    except Exception as e:
        logger.error(f"Error in copy_dicom_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Export - Series Preparation")
def series_preparation_task(self, copy_dicom_task_results):
    """
    This task will prepare the series for deidentification.
    It will return a dictionary with the following keys:
        - status (success, partial_failure, or failure)
        - message (message to be displayed)
        - separated_series_path_folders (list of paths to folders where series were successfully separated)
        - series_processing_ids (list of UUIDs of created DicomSeriesProcessingModel entries)
    """
    try:
        # Add task_id to the input data
        copy_dicom_task_results['task_id'] = self.request.id
        series_preparation_task_results = series_preparation(copy_dicom_task_results)   
        logger.info(f"Series preparation task results: {series_preparation_task_results}")
        return series_preparation_task_results
    except Exception as e:
        logger.error(f"Error in series_preparation_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )



@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Export - Match Autosegmentation Template")
def match_autosegmentation_template_task(self, series_preparation_task_results):
    """
    This task will match the autosegmentation template to the series.
    It will return a dictionary with the following keys:
        - status (success, partial_failure, or failure)     
        - message (message to be displayed)
        - series_folder_path (path to the folder where the series folder is now located)
        - deidentification_status (boolean indicating if the series is ready for deidentification)
        - failed_series (list of series IDs that failed to process)
        - successful_series (list of series IDs that were processed successfully)
    """
    try:    
        # Add task_id to the input data
        series_preparation_task_results['task_id'] = self.request.id
        match_autosegmentation_template_task_results = match_autosegmentation_template(series_preparation_task_results)
        logger.info(f"Match autosegmentation template task results: {match_autosegmentation_template_task_results}")
        return match_autosegmentation_template_task_results
    except Exception as e:
        logger.error(f"Error in match_autosegmentation_template_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Export - Deidentify DICOM Series")
def deidentify_dicom_series_task(self, match_autosegmentation_template_task_results):
    """
    This task will deidentify the DICOM files in the series.
    It will return a dictionary with the following keys:
        - status (success, partial_failure, or failure)
        - message (message to be displayed)
        - deidentified_series_path_folders (list of paths to folders where series were successfully deidentified)
        - deidentified_series_processing_ids (list of UUIDs of created DicomSeriesProcessingModel entries)
    """
    try:
        # Add task_id to the input data
        match_autosegmentation_template_task_results['task_id'] = self.request.id
        deidentify_dicom_task_results = deidentify_dicom_series(match_autosegmentation_template_task_results)
        logger.info(f"Deidentify dicom task results: {deidentify_dicom_task_results}")      
        return deidentify_dicom_task_results
    except Exception as e:
        logger.error(f"Error in deidentify_dicom_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds 
            max_retries=3  # override max retries for this specific retry
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Export - Send DICOM to Remote Server")
def send_dicom_to_remote_server_task(self, deidentify_dicom_series_task_results):
    """
    This task will send the DICOM series to the remote server.
    """
    try:    
        # Add task_id to the input data
        deidentify_dicom_series_task_results['task_id'] = self.request.id
        send_dicom_to_remote_server(deidentify_dicom_series_task_results)
        logger.info(f"Send dicom to remote server task results: {deidentify_dicom_series_task_results}")
        return deidentify_dicom_series_task_results
    except Exception as e:
        logger.error(f"Error in send_dicom_to_remote_server_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )

@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Export - Pipeline to export DICOM to Remote Server")
def send_dicom_to_remote_server_pipeline(self, target_path=None):
    """
    This task chains together all the DICOM processing tasks in sequence:
    1. Copy DICOM files using the copy_dicom_task
    2. Prepare series using the series_preparation_task
    3. Match autosegmentation template using the match_autosegmentation_template_task
    4. Deidentify DICOM series using the deidentify_dicom_series_task
    5. Send to remote server using the send_dicom_to_remote_server_task
    
    Args:
        target_path: Optional target path for copying files
    """
    try:
        # Get the DicomPathConfig instance
        path_config = DicomPathConfig.get_instance()
        # Get a safe path using the get_safe_path method
        datastore_path = path_config.get_safe_path()
        if datastore_path is None:
            raise ValueError("No valid datastore path configured")
            
        # Create the task chain
        task_chain = chain(
            copy_dicom_task.s(str(datastore_path), str(target_path) if target_path else None, task_id=self.request.id),
            series_preparation_task.s(),
            match_autosegmentation_template_task.s(),
            deidentify_dicom_series_task.s(),
            send_dicom_to_remote_server_task.s()
        )
        
        # Execute the chain
        result = task_chain.apply_async()
        logger.info(f"Started DICOM processing pipeline with chain ID: {result.id}")
        return {"status": "success", "chain_id": result.id}
    except Exception as e:
        logger.error(f"Error in process_dicom_pipeline: {e}")
        raise self.retry(
            exc=e,
            countdown=60,
            max_retries=3
        )
    

## DICOM Import Tasks

@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Import - Poll Pending Transfers")
def poll_pending_transfers_task(self):
    """
    This task will poll the remote server for the status of the DICOM series.
    """
    try:
        poll_pending_transfers_results = poll_pending_transfers()
        logger.info(f"Poll remote server task results: {poll_pending_transfers_results}")
        return poll_pending_transfers_results
    except Exception as e:
        logger.error(f"Error in poll_pending_transfers_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )
    
 
@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Import - Reidentify RTSTRUCT File")
def reidentify_rtstruct_file_task(self, poll_pending_transfers_results):
    """
    This task will reidentify the RTSTRUCT files and export them to the datastore folder path if found.
    """
    try:
        reidentify_rtstruct_file_results = reidentify_rtstruct_file_and_export_to_datastore(poll_pending_transfers_results)
        logger.info(f"Reidentify rtstruct file task results: {reidentify_rtstruct_file_results}")
        return reidentify_rtstruct_file_results
    except Exception as e:
        logger.error(f"Error in reidentify_rtstruct_file_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )       



# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def export_rtstruct_task(self, reidentify_rtstruct_file_results):
#     """
#     This task will export the RTSTRUCT files to the datastore.
#     """
#     try:
#         export_rtstruct_results = export_rtstruct(reidentify_rtstruct_file_results)
#         logger.info(f"Export rtstruct file task results: {export_rtstruct_results}")
#         return export_rtstruct_results
#     except Exception as e:
#         logger.error(f"Error in export_rtstruct_task: {e}")
#         raise self.retry(
#             exc=e,
#             countdown=60,  # retry after 60 seconds
#             max_retries=3  # override max retries for this specific retry
#         )


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name = "DICOM Import - Pipeline to import RTSTRUCT from remote server")  
def import_rtstruct_from_remote_server_pipeline(self, target_path=None):
    """
    This task chains together all the DICOM processing tasks in sequence:
    1. Poll pending transfers using the poll_pending_transfers_task
    2. Reidentify RTSTRUCT files using the reidentify_rtstruct_file_task
    3. Export RTSTRUCT files using the export_rtstruct_task
    """
    try:
        task_chain = chain(
            poll_pending_transfers_task.s(),
            reidentify_rtstruct_file_task.s(),
            # export_rtstruct_task.s()
        )

        result = task_chain.apply_async()
        logger.info(f"Started Import RTSTRUCT from remote server pipeline with chain ID: {result.id}")
        return {"status": "success", "chain_id": result.id}
    except Exception as e:
        logger.error(f"Error in Importing RTSTRUCT from remote server pipeline: {e}")
        raise self.retry(
            exc=e,
            countdown=60,
            max_retries=3
        )


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name="DICOM Import - Notify Remote Server about completed Transfers")
def notify_remote_server_task(self):
    """
    This task will notify the remote server that the DICOM RTStructureSet has been received.
    """
    try:
        notify_completed_transfers_results = notify_completed_transfers()
        logger.info(f"Notify remote server task results: {notify_completed_transfers_results}")
        return notify_completed_transfers_results
    except Exception as e:
        logger.error(f"Error in notify_completed_transfers_task: {e}")
        raise self.retry(
            exc=e,
            countdown=60,  # retry after 60 seconds
            max_retries=3  # override max retries for this specific retry
        )