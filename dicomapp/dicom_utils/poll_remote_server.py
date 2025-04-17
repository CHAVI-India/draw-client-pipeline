import logging
import hashlib
import requests
import os
from pathlib import Path
from api_client.models import DicomTransfer, SystemSettings
from api_client.api_utils.dicom_export import DicomExporter
from api_client.api_utils.proxy_config import get_proxy_settings
from django.conf import settings
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
    If the RTSTRUCT is successfully downloaded and verified, the server is notified.
    If the server is notified, the transfer is marked as completed.
    Returns a dictionary containing:
        - status: overall status of the polling operation
        - message: descriptive message about the operation
        - rtstruct_paths: list of successfully downloaded RTSTRUCT file paths
    """
    # Initialize results dictionary
    results = {
        'status': 'success',
        'message': '',
        'rtstruct_paths': []
    }
    
    try:
        exporter = DicomExporter()  # DicomExporter already has proxy configuration
        system_settings = SystemSettings.load()
        
        # Create output folder if it doesn't exist - fix the Path handling
        output_folder = Path(os.path.join(settings.BASE_DIR,'folders' ,'folder_deidentified_rtstruct'))
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)
        
        pending_transfers = DicomTransfer.objects.filter(
            status__in=['SENT', 'PROCESSING']
        )

        logger.info(f"Polling for {pending_transfers.count()} pending transfers")
        
        # Create a session with proxy settings for downloads
        session = requests.Session()
        session.proxies.update(get_proxy_settings())

        for transfer in pending_transfers:
            try:
                # Update polling attempt counters
                transfer.update_poll_attempt()
                
                # Log the transfer being checked
                logger.info(f"Checking transfer ID: {transfer.id}, Server Token: {transfer.server_token}, Poll Attempts: {transfer.poll_attempts}")
                
                # Construct the status endpoint URL for logging
                status_endpoint = system_settings.status_endpoint.format(task_id=transfer.server_token)
                logger.info(f"Making status request to: {system_settings.api_base_url}/{status_endpoint}")
                
                # Check status with server using DicomExporter's authenticated request
                response = exporter._make_request(
                    'GET',
                    system_settings.status_endpoint.format(task_id=transfer.server_token)
                )
                
                # Log the full response for debugging
                logger.info(f"Response for transfer {transfer.id}: {response}")
                
                status = response.get('status', 'UNKNOWN')
                logger.info(f"Transfer {transfer.id} status: {status}")
                
                # Update the server_status field with the status from the server
                transfer.update_server_status(status)
                
                if status in ['SEGMENTATION RETRIEVED', 'SEGMENTATION COMPLETE']:
                    logger.info(f"Transfer {transfer.id} completed. Proceeding to download RTSTRUCT file.")
                    
                    try:
                        # Log download attempt
                        download_endpoint = system_settings.download_endpoint.format(task_id=transfer.server_token)
                        download_url = f"{system_settings.api_base_url}/{download_endpoint}"
                        logger.info(f"Attempting to download RTSTRUCT from: {download_url}")
                        
                        # Make a direct request to get the RTSTRUCT file with the bearer token
                        headers = {
                            'Authorization': f'Bearer {system_settings.get_bearer_token()}'
                        }
                        
                        # Download RTSTRUCT file using session with proxy settings
                        download_response = session.get(
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
                        rtstruct_path = Path(output_folder) / f"{transfer.series_instance_uid}_rtstruct.dcm"
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
                        
                        # Convert Path object to string before appending
                        results['rtstruct_paths'].append(str(rtstruct_path))

                        # Notify the server that the transfer has been completed.
                        try:

                            response = exporter._make_request(
                                'POST',
                                system_settings.notify_endpoint.format(task_id = transfer.server_token)
                            )
                            logger.info(f"Response: {response}")
                            # Verify response format
                            if response.get('message') == "Transfer confirmation received, files cleaned up":
                                transfer.server_notified = True
                                transfer.status = 'COMPLETED_NOTIFIED'
                                transfer.save()
                                logger.info(f"Successfully notified completion of transfer {transfer.id}")

                            else:
                                logger.info(f"Failed to notify server about completed transfer for {transfer.id}")  
                        except Exception as e:
                            warning_msg = f"Warning Failed to notify server: {str(e)}"
                            logger.warning(warning_msg)        

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
                logger.warning(f"Error checking transfer {transfer.id}: {str(e)}")
                # Don't mark as failed here as it might be a temporary network issue
                
    except Exception as e:
        logger.error(f"Error in poll_pending_transfers: {str(e)}")
        results['status'] = 'error'
        results['message'] = str(e)
    
    logger.info(f"Finished polling for pending transfers. Results: {results}")
    return results
