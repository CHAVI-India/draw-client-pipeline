import logging
from django.db import transaction
from ..models import DicomTransfer, SystemSettings
from .dicom_export import DicomExporter

logger = logging.getLogger(__name__)

def notify_completed_transfers():
    """
    Send status updates to server for completed transfers that haven't been notified.
    """
    try:
        exporter = DicomExporter()
        settings = SystemSettings.load()
        
        # Use select_for_update to prevent concurrent access
        with transaction.atomic():
            completed_transfers = DicomTransfer.objects.select_for_update().filter(
                status='COMPLETED',
                server_notified=False
            )
            
            for transfer in completed_transfers:
                try:
                    # Send notification to server
                    response = exporter._make_request(
                        'POST',
                        settings.notify_endpoint.format(task_id=transfer.server_token),
                        json={'status': 'COMPLETED'}
                    )
                    
                    # If we get here, the request was successful since _make_request raises on error
                    transfer.server_notified = True
                    transfer.save()
                    logger.info(f"Successfully notified completion of transfer {transfer.id}")
                        
                except Exception as e:
                    logger.error(f"Error notifying transfer {transfer.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in notify_completed_transfers: {str(e)}")
