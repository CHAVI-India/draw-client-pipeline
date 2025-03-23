import logging
import os
from pathlib import Path
from ..models import DicomTransfer
from django.conf import settings

logger = logging.getLogger('api_client')

def cleanup_old_transfers():
    """
    Clean up completed transfers by removing their archived files.
    Only processes transfers that are in COMPLETED status and have not been cleaned up yet.
    """
    try:
        # Get archive folder path - convert to Path object
        archive_folder = Path(os.path.join(settings.BASE_DIR, 'folder_archive'))

        
        # Get completed transfers that haven't been cleaned up
        completed_transfers = DicomTransfer.objects.filter(
            status='COMPLETED',
            cleaned_up=False
        )
        
        for transfer in completed_transfers:
            try:
                # Delete archived files
                archive_path = archive_folder / transfer.study_instance_uid / transfer.series_instance_uid
                if archive_path.exists():
                    for file_path in archive_path.glob('*'):
                        file_path.unlink()
                    archive_path.rmdir()
                    
                    # Try to remove parent study directory if empty
                    study_path = archive_path.parent
                    if not any(study_path.iterdir()):
                        study_path.rmdir()
                
                # Mark as cleaned up
                transfer.cleaned_up = True
                transfer.save()
                logger.info(f"Successfully cleaned up archived files for transfer {transfer.id}")
                
            except Exception as e:
                logger.error(f"Error cleaning up transfer {transfer.id}: {str(e)}")
                
    except Exception as e:
        logger.error(f"Error in cleanup_old_transfers: {str(e)}")
