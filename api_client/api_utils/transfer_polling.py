import logging
import hashlib
import requests
from pathlib import Path
from ..models import DicomTransfer, SystemSettings, FolderPaths
from .dicom_export import DicomExporter

logger = logging.getLogger(__name__)

def compute_file_checksum(file_path):
    """
    Compute SHA-256 checksum of a file.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def poll_pending_transfers():
    """
    Poll the server for all pending RTSTRUCT transfers.
    """
    try:
        exporter = DicomExporter()
        settings = SystemSettings.load()
        folder_paths = FolderPaths.load()
        
        pending_transfers = DicomTransfer.objects.filter(
            status__in=['SENT', 'PROCESSING']
        )

        logger.info(f"Polling for {pending_transfers.count()} pending transfers")

        for transfer in pending_transfers:
            try:
                # Update polling attempt counters
                transfer.update_poll_attempt()
                
                # Log the transfer being checked
                logger.info(f"Checking transfer ID: {transfer.id}, Server Token: {transfer.server_token}, Poll Attempts: {transfer.poll_attempts}")
                
                # Construct the status endpoint URL for logging
                status_endpoint = settings.status_endpoint.format(task_id=transfer.server_token)
                logger.info(f"Making status request to: {settings.api_base_url}/{status_endpoint}")
                
                # Check status with server using DicomExporter's authenticated request
                response = exporter._make_request(
                    'GET',
                    settings.status_endpoint.format(task_id=transfer.server_token)
                )
                
                # Log the full response for debugging
                logger.info(f"Response for transfer {transfer.id}: {response}")
                
                status = response.get('status', 'UNKNOWN')
                logger.info(f"Transfer {transfer.id} status: {status}")
                
                # Update the server_status field with the status from the server
                transfer.update_server_status(status)
                
                if status == 'SEGMENTATION COMPLETED':
                    logger.info(f"Transfer {transfer.id} completed. Proceeding to download RTSTRUCT file.")
                    
                    try:
                        # Log download attempt
                        download_endpoint = settings.download_endpoint.format(task_id=transfer.server_token)
                        download_url = f"{settings.api_base_url}/{download_endpoint}"
                        logger.info(f"Attempting to download RTSTRUCT from: {download_url}")
                        
                        # Make a direct request to get the RTSTRUCT file with the bearer token
                        headers = {
                            'Authorization': f'Bearer {settings.get_bearer_token()}'
                        }
                        
                        # Download RTSTRUCT file using requests to get access to headers
                        download_response = requests.get(
                            download_url,
                            headers=headers,
                            stream=True
                        )
                        
                        # Check for successful response
                        if download_response.status_code != 200:
                            error_msg = f"Failed to download RTSTRUCT. Status code: {download_response.status_code}, Response: {download_response.text}"
                            logger.error(error_msg)
                            transfer.mark_as_failed(error_msg)
                            continue
                        
                        # Log download response headers
                        logger.info(f"Download response headers for transfer {transfer.id}: {dict(download_response.headers)}")
                        
                        # Get checksum from header
                        expected_checksum = download_response.headers.get('X-File-Checksum')
                        
                        if not expected_checksum:
                            logger.warning(f"No X-File-Checksum header received for transfer {transfer.id}. Will compute checksum locally.")
                        
                        # Save RTSTRUCT file
                        rtstruct_path = Path(folder_paths.output_folder) / f"{transfer.series_instance_uid}_rtstruct.dcm"
                        logger.info(f"Saving RTSTRUCT to: {rtstruct_path}")
                        
                        with open(rtstruct_path, 'wb') as f:
                            for chunk in download_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        # Compute checksum of downloaded file
                        actual_checksum = compute_file_checksum(rtstruct_path)
                        logger.info(f"Computed checksum for {rtstruct_path}: {actual_checksum}")
                        
                        # Verify checksum if provided in header
                        if expected_checksum:
                            logger.info(f"Comparing checksums - Expected: {expected_checksum}, Actual: {actual_checksum}")
                            
                            if actual_checksum.lower() != expected_checksum.lower():
                                error_msg = f"Checksum mismatch for RTSTRUCT. Expected: {expected_checksum}, Got: {actual_checksum}"
                                logger.error(error_msg)
                                transfer.mark_as_failed(error_msg)
                                if rtstruct_path.exists():
                                    rtstruct_path.unlink()
                                continue
                        
                        # Update transfer record with successful verification
                        transfer.rtstruct_checksum = actual_checksum
                        transfer.rtstruct_checksum_verified = True
                        transfer.mark_as_completed(str(rtstruct_path))
                        logger.info(f"Transfer {transfer.id} marked as completed with RTSTRUCT at {rtstruct_path}")

                        # Clean up zip file after successful RTSTRUCT receipt
                        zip_path = Path(transfer.zip_file_path)
                        if zip_path.exists():
                            try:
                                zip_path.unlink()
                                logger.info(f"Cleaned up zip file for transfer {transfer.id}: {zip_path}")
                            except Exception as e:
                                logger.warning(f"Failed to clean up zip file for transfer {transfer.id}: {str(e)}")

                        logger.info(f"Successfully verified and saved RTSTRUCT for transfer {transfer.id}")
                        
                    except Exception as e:
                        error_msg = f"Error downloading/verifying RTSTRUCT: {str(e)}"
                        logger.error(error_msg)
                        transfer.mark_as_failed(error_msg)
                        if 'rtstruct_path' in locals() and rtstruct_path.exists():
                            rtstruct_path.unlink()
                        
                elif status == 'FAILED':
                    # Handle failure
                    error_msg = response.get('error', 'Unknown error')
                    logger.error(f"Transfer {transfer.id} failed: {error_msg}")
                    transfer.mark_as_failed(error_msg)
                else:
                    # For other states, just update the server_status field
                    # The status field is already updated by the update_server_status method
                    logger.info(f"Transfer {transfer.id} has server status: {status}, client status remains: {transfer.status}")
                
            except Exception as e:
                logger.error(f"Error checking transfer {transfer.id}: {str(e)}")
                # Don't mark as failed here as it might be a temporary network issue
                
    except Exception as e:
        logger.error(f"Error in poll_pending_transfers: {str(e)}")
