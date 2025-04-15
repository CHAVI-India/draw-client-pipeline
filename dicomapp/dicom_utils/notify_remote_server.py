import logging
from django.db import transaction
from api_client.models import DicomTransfer, SystemSettings
from api_client.api_utils.dicom_export import DicomExporter

logger = logging.getLogger(__name__)

def notify_completed_transfers():
    """
    Send status updates to server for completed transfers that haven't been notified.
    This confirms successful RTSTRUCT transfer and allows server cleanup.
    """
    try:
        exporter = DicomExporter()
        system_settings = SystemSettings.load()
        
        # Use select_for_update to prevent concurrent access
        with transaction.atomic():
            completed_transfers = DicomTransfer.objects.select_for_update().filter(
                status='COMPLETED',
                server_notified=False  # For BooleanField, we can use False directly
            )
            
            for transfer in completed_transfers:
                try:
                    # Send notification to server using the endpoint from settings
                    response = exporter._make_request(
                        'POST',
                        system_settings.notify_endpoint.format(task_id=transfer.server_token),
                    )
                    logger.info(f"Response: {response}")
                    # Verify response format
                    if response.get('message') == "Transfer confirmation received, files cleaned up":
                        transfer.server_notified = True
                        transfer.status = 'COMPLETED_NOTIFIED'
                        transfer.save()
                        logger.info(f"Successfully notified completion of transfer {transfer.id}")
                    else:
                        logger.error(f"Unexpected response format for transfer {transfer.id}")
                        
                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg:
                        logger.error(f"Authentication failed for transfer {transfer.id}: {error_msg}")
                    elif "404" in error_msg:
                        logger.error(f"Transaction not found for transfer {transfer.id}: {error_msg}")
                    elif "500" in error_msg:
                        logger.error(f"Server error during cleanup for transfer {transfer.id}: {error_msg}")
                    else:
                        logger.error(f"Error notifying transfer {transfer.id}: {error_msg}")
                
    except Exception as e:  
        logger.error(f"Error in notify_completed_transfers: {str(e)}")
        raise
