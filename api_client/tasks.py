# import os
# from celery import shared_task, chain
# from django.conf import settings
# from logging import getLogger 
# from api_client.api_utils import scan_dicom_folder, poll_pending_transfers, notify_completed_transfers, cleanup_old_transfers
# from api_client.models import *

# logger = getLogger('api_client')

# @shared_task(name="api_client.tasks.scan_dicom_folder_task")
# def scan_dicom_folder_task(delta_time=10):
#     """
#     This task will scan the dicom folder and send the dicom files in a zip file to the server.
#     """
#     try:
#         task_id = scan_dicom_folder_task.request.id
#         logger.info(f"[Task ID: {task_id}] Starting DICOM folder scan task")
#         scan_dicom_folder()
#         logger.info(f"[Task ID: {task_id}] DICOM folder scan task completed successfully")
#         return {"status": "success", "message": "DICOM folder scan task completed successfully"}
#     except Exception as e:
#         task_id = getattr(scan_dicom_folder_task, 'request', None)
#         task_id = task_id.id if task_id else 'unknown'
#         logger.error(f"[Task ID: {task_id}] Error during DICOM folder scan task: {str(e)}")
#         raise e

# @shared_task(name="api_client.tasks.poll_pending_transfers_task")

# def poll_pending_transfers_task():
#     """
#     This task will poll the status of the pending transfers and download the RTSTRUCT file from the server if they are available.
#     """
#     try:
#         task_id = poll_pending_transfers_task.request.id
#         logger.info(f"[Task ID: {task_id}] Starting pending transfers poll task")
#         poll_pending_transfers()    
#         logger.info(f"[Task ID: {task_id}] Pending transfers poll task completed successfully")
#         return {"status": "success", "message": "Pending transfers poll task completed successfully"}
#     except Exception as e:
#         task_id = getattr(poll_pending_transfers_task, 'request', None)
#         task_id = task_id.id if task_id else 'unknown'
#         logger.error(f"[Task ID: {task_id}] Error during pending transfers poll task: {str(e)}")
#         raise e

# @shared_task(name="api_client.tasks.notify_completed_transfers_task")
# def notify_completed_transfers_task():
#     """
#     This task will notify the server that the transfers are completed.
#     """
#     try:
#         task_id = notify_completed_transfers_task.request.id
#         logger.info(f"[Task ID: {task_id}] Starting notify completed transfers task")
#         notify_completed_transfers()
#         logger.info(f"[Task ID: {task_id}] Notify completed transfers task completed successfully")
#         return {"status": "success", "message": "Notify completed transfers task completed successfully"}
#     except Exception as e:
#         task_id = getattr(notify_completed_transfers_task, 'request', None)
#         task_id = task_id.id if task_id else 'unknown'
#         logger.error(f"[Task ID: {task_id}] Error during notify completed transfers task: {str(e)}")
#         raise e
    

# @shared_task(name="api_client.tasks.cleanup_old_transfers_task")
# def cleanup_old_transfers_task():
#     """
#     This task will cleanup the old transfers.
#     """
#     try:
#         task_id = cleanup_old_transfers_task.request.id
#         logger.info(f"[Task ID: {task_id}] Starting cleanup old transfers task")
#         cleanup_old_transfers()
#         logger.info(f"[Task ID: {task_id}] Cleanup old transfers task completed successfully")
#         return {"status": "success", "message": "Cleanup old transfers task completed successfully"}
#     except Exception as e:
#         task_id = getattr(cleanup_old_transfers_task, 'request', None)
#         task_id = task_id.id if task_id else 'unknown'
#         logger.error(f"[Task ID: {task_id}] Error during cleanup old transfers task: {str(e)}")
#         raise e