import logging
import requests
import os
from django.utils import timezone
from pathlib import Path
from api_client.models import DicomTransfer, SystemSettings
from django.conf import settings
from api_client.api_utils.proxy_config import get_proxy_settings

logger = logging.getLogger('api_client')

class DicomExporter:
    """Handles DICOM file exports and API interactions."""
    
    def __init__(self):
        """Initialize exporter with settings."""
        self.settings = SystemSettings.load()
        self.session = requests.Session()
        self.session.proxies.update(get_proxy_settings())

    def set_test_token(self, token):
        """
        Set a token directly for testing purposes.
        This bypasses the encryption/decryption process.
        
        Args:
            token: The bearer token to use for API requests
        """
        self._test_token = token
        logger.info("Test token set successfully")

    def _get_headers(self):
        """Get headers for API requests."""
        try:
            # Use test token if available (for testing purposes)
            if hasattr(self, '_test_token') and self._test_token:
                logger.info("Using test token for authentication")
                bearer_token = self._test_token
            else:
                bearer_token = self.settings.get_bearer_token()
                
            if not bearer_token:
                logger.error("Bearer token not found or could not be decrypted")
                raise ValueError("Bearer token not found. Please ensure authentication is set up correctly.")
            
            # Check if the token is a JWT token (starts with eyJ)
            # This indicates it might not have been encrypted properly
            if bearer_token.startswith('eyJ'):
                # The token appears to be a raw JWT token
                logger.warning("Token appears to be a raw JWT token. It may not have been encrypted properly.")
                logger.warning("This is expected if you're using a token that was set before the encryption fix.")
                # Continue using it as-is
            
            headers = {
                'Authorization': f'Bearer {bearer_token}',
                'Accept': 'application/json',
            }
            # Don't log the full token for security reasons
            safe_headers = headers.copy()
            if 'Authorization' in safe_headers and safe_headers['Authorization']:
                token_parts = safe_headers['Authorization'].split(' ')
                if len(token_parts) > 1:
                    token = token_parts[1]
                    safe_headers['Authorization'] = f"{token_parts[0]} {token[:10]}...{token[-5:]}"
            
            logger.debug(f"Headers (token partially hidden): {safe_headers}")
            return headers
        except Exception as e:
            logger.error(f"Error creating headers: {type(e).__name__}: {str(e)}")
            raise
        
    def _refresh_token(self):
        """Refresh the bearer token using the refresh token."""
        refresh_token = self.settings.get_refresh_token()
        if not refresh_token:
            raise ValueError("Refresh token not found. Please ensure authentication is set up correctly.")
            
        try:
            response = requests.post(
                f"{self.settings.api_base_url.rstrip('/')}/auth/refresh",
                headers={'Authorization': f'Bearer {refresh_token}'},
                json={'client_id': self.settings.client_id}
            )
            response.raise_for_status()
            data = response.json()
            
            # Update tokens in settings
            self.settings.set_bearer_token(data['access_token'])
            if 'refresh_token' in data:  # Update refresh token if provided
                self.settings.set_refresh_token(data['refresh_token'])
            self.settings.token_expiry = timezone.now() + timezone.timedelta(seconds=data.get('expires_in', 3600))
            self.settings.save()
            
            return data['access_token']
        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise
        
    def _make_request(self, method, endpoint, **kwargs):
        """Make an API request with retry logic."""
        url = f"{self.settings.api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        retries = 0
        token_refreshed = False
        
        while retries < self.settings.max_retries:
            try:
                logger.debug(f"Making {method} request to {url}")
                logger.debug(f"Request headers: {self._get_headers()}")
                if 'files' in kwargs:
                    pass
                    #logger.debug(f"Files in request: {kwargs['files']}")
                if 'data' in kwargs:
                    pass
                    #logger.debug(f"Form data in request: {kwargs['data']}")
                if 'json' in kwargs:
                    pass   
                    #logger.debug(f"Request body: {kwargs['json']}")
                if 'params' in kwargs:
                    pass
                    #logger.debug(f"Request params: {kwargs['params']}")
                #logger.debug(f"Request kwargs: {kwargs}")
                
                response = self.session.request(
                    method,
                    url,
                    headers=self._get_headers(),
                    **kwargs
                )
                
                # Handle token expiration
                if response.status_code == 401 and not token_refreshed:
                    logger.info("Token expired, attempting to refresh...")
                    self._refresh_token()
                    token_refreshed = True
                    continue
                
                try:
                    error_detail = response.json() if not response.ok else None
                except:
                    error_detail = response.text if not response.ok else None
                
                if not response.ok:
                    logger.error(f"Request failed with status {response.status_code}. Error details: {error_detail}")
                    #logger.info(f"Files in request: {list(kwargs.get('files', {}).keys())}")
                    #logger.info(f"Form data in request: {kwargs.get('data', {})}")
                    #logger.info(f"Headers sent: {self._get_headers()}")
                    #logger.info(f"Response headers: {response.headers}")
                
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                retries += 1
                if retries == self.settings.max_retries:
                    raise e
                logger.warning(f"API request failed, attempt {retries} of {self.settings.max_retries}: {str(e)}")
        
    def _check_url_accessibility(self, url):
        """Check if a URL is accessible with a simple GET request."""
        try:
            logger.info(f"Testing URL accessibility: {url}")
            response = self.session.get(url, timeout=5)
            logger.info(f"URL accessibility test result: {response.status_code}")
            return response.status_code, response.text
        except Exception as e:
            logger.error(f"URL accessibility test failed: {str(e)}")
            return None, str(e)

    def _check_network_environment(self):
        """Check network environment for potential issues."""
        try:
            # Get proxy settings from our configuration
            proxies = get_proxy_settings()
            logger.info(f"Proxy settings: {proxies}")
            
            # Log requests library version
            logger.info(f"Requests library version: {requests.__version__}")
            
            # Check if we can reach a public website
            try:
                test_response = self.session.get('https://www.google.com', timeout=5)
                logger.info(f"Public internet access test: {test_response.status_code}")
            except Exception as e:
                logger.error(f"Public internet access test failed: {str(e)}")
                
            return proxies
        except Exception as e:
            logger.error(f"Error checking network environment: {str(e)}")
            return None

    def initiate_transfer(self, zip_file_path: str, study_uid: str, series_uid: str, zip_checksum: str, bypass_health_check=False) -> DicomTransfer:
        """
        Start a new DICOM transfer process.
        
        Args:
            zip_file_path: Path to the DICOM zip file
            study_uid: Study Instance UID
            series_uid: Series Instance UID
            zip_checksum: SHA-256 checksum of the zip file
            bypass_health_check: If True, skip the API health check
            
        Returns:
            DicomTransfer: Created transfer record
            
        Raises:
            FileNotFoundError: If zip file doesn't exist
            ValueError: If UIDs are invalid
        """
        # Check network environment
        self._check_network_environment()
        
        # First check basic URL accessibility
        api_base_url = self.settings.api_base_url.rstrip('/')
        status_code, response_text = self._check_url_accessibility(api_base_url)
        logger.info(f"Base API URL accessibility: {status_code}")
        
        # Verify API health before proceeding (unless bypassed)
        health_check_passed = False
        if not bypass_health_check:
            # Construct health check URL - ensure it's correct
            health_url = f"{api_base_url}/api/health/"
            logger.info(f"Using health check URL: {health_url}")
            try:
                headers = self._get_headers()
                logger.debug(f"Health check headers: {headers}")
                try:
                    health_response = requests.get(health_url, headers=headers, timeout=10)
                    logger.debug(f"Health check response status: {health_response.status_code}")
                    if not health_response.ok:
                        logger.error(f"Health check failed with status {health_response.status_code}")
                        logger.error(f"Response content: {health_response.text}")
                        logger.error(f"Response headers: {health_response.headers}")
                        
                        # Try without authentication headers as a fallback
                        logger.info("Attempting health check without authentication headers")
                        fallback_headers = {'Accept': 'application/json'}
                        fallback_response = requests.get(health_url, headers=fallback_headers, timeout=10)
                        if fallback_response.ok:
                            logger.info(f"Health check without auth successful: {fallback_response.json()}")
                            health_check_passed = True
                        else:
                            logger.error(f"Health check without auth also failed: {fallback_response.status_code}")
                            raise ValueError(f"API health check failed with status {health_response.status_code}")
                    else:
                        logger.info(f"API health check successful: {health_response.json()}")
                        health_check_passed = True
                except requests.exceptions.RequestException as req_err:
                    logger.error(f"Health check request error: {type(req_err).__name__}: {str(req_err)}")
                    if hasattr(req_err, 'response') and req_err.response:
                        logger.error(f"Response status: {req_err.response.status_code}")
                        logger.error(f"Response content: {req_err.response.text}")
                        logger.error(f"Response headers: {req_err.response.headers}")
                    
                    # Try without authentication as a fallback for connection issues
                    try:
                        logger.info("Attempting health check without authentication due to request exception")
                        fallback_headers = {'Accept': 'application/json'}
                        fallback_response = requests.get(health_url, headers=fallback_headers, timeout=10)
                        if fallback_response.ok:
                            logger.info(f"Health check without auth successful: {fallback_response.json()}")
                            health_check_passed = True
                        else:
                            logger.error(f"Health check without auth also failed: {fallback_response.status_code}")
                            raise req_err
                    except Exception as fallback_err:
                        logger.error(f"Fallback health check failed: {str(fallback_err)}")
                        raise req_err
            except Exception as e:
                logger.error(f"API health check failed: {type(e).__name__}: {str(e)}")
                raise
        else:
            logger.info("Health check bypassed as requested")
            health_check_passed = True
        
        # Create transfer record
        transfer = DicomTransfer.objects.create(
            study_instance_uid=study_uid,
            series_instance_uid=series_uid,
            zip_file_path=zip_file_path,
            zip_checksum=zip_checksum,
            status='PENDING'
        )

        try:
            # Verify file exists and can be opened
            zip_path = Path(zip_file_path)
            if not zip_path.exists():
                raise FileNotFoundError(f"Zip file not found: {zip_file_path}")
            
            # Log file size before upload
            file_size = zip_path.stat().st_size
            if file_size == 0:
                raise ValueError(f"Zip file is empty: {zip_file_path}")
            logger.info(f"Uploading file {zip_file_path} (size: {file_size} bytes)")
            
            # Upload to server
            with open(zip_file_path, 'rb') as f:
                file_content = f.read()
                if not file_content:
                    raise ValueError(f"Failed to read content from zip file: {zip_file_path}")
                
                logger.info(f"Preparing to upload file {zip_file_path} (size: {file_size} bytes)")
                logger.info(f"File content verification: {'Valid' if file_content else 'Empty'}")
                logger.info(f"Upload endpoint: {self.settings.upload_endpoint}")
                
                # Use the filename from the zip_file_path
                upload_filename = Path(zip_file_path).name
                logger.info(f"Using upload filename: {upload_filename}")
                
                response = self._make_request(
                    'POST',
                    self.settings.upload_endpoint,
                    files={
                        'file': (upload_filename, file_content, 'application/zip')
                    },
                    data={
                        'checksum': zip_checksum,
                        'client_id': self.settings.client_id
                    }
                )
            
            # Update transfer record with transaction token
            transfer.server_task_id = response.get('transaction_token')
            transfer.server_token = response.get('transaction_token')
            # Convert absolute path to relative path before saving
            try:
                zip_path = Path(zip_file_path)
                transfer.zip_file_path = str(zip_path.relative_to(settings.BASE_DIR))
            except ValueError:
                # If the path is not relative to BASE_DIR, store it as-is
                transfer.zip_file_path = zip_file_path
            transfer.mark_as_sent()
            
            logger.info(f"Transfer initiated successfully. ID: {transfer.id}, Transaction Token: {transfer.server_token}, Token: {transfer.server_token}")
            
        except Exception as e:
            error_msg = f"Failed to initiate transfer: {str(e)}"
            logger.error(error_msg)
            transfer.mark_as_failed(error_msg)
            raise
        
        return transfer
