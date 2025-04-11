import os
import requests
from urllib.parse import urljoin
from typing import Optional, Dict, Any, BinaryIO
import logging
from requests.exceptions import RequestException
from api_client.api_utils.proxy_config import get_proxy_settings

logger = logging.getLogger(__name__)

class DrawAPIClient:
    """Client for interacting with the DRAW API."""
    
    def __init__(self, base_url: str, api_key: str, settings: 'SystemSettings'):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL for the DRAW API
            api_key: API key for authentication
            settings: SystemSettings instance containing endpoint patterns
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.settings = settings
        self.session = requests.Session()
        self.session.proxies.update(get_proxy_settings())
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Accept': 'application/json',
        }
        
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        **kwargs
    ) -> requests.Response:
        """
        Make an API request.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional arguments for requests.request
            
        Returns:
            Response from the API
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        kwargs['headers'] = {**kwargs.get('headers', {}), **self._get_headers()}
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response
        
    def upload_dicom(
        self, 
        zip_file: BinaryIO,
        study_uid: str,
        series_uid: str
    ) -> Dict[str, Any]:
        """
        Upload a DICOM zip file for segmentation.
        
        Args:
            zip_file: File-like object containing the zipped DICOM files
            study_uid: Study Instance UID
            series_uid: Series Instance UID
            
        Returns:
            Dict containing task_id and token for tracking the segmentation
        """
        files = {'file': zip_file}
        data = {
            'study_uid': study_uid,
            'series_uid': series_uid,
        }
        
        response = self._make_request('POST', self.settings.upload_endpoint, files=files, data=data)
        return response.json()
        
    def check_segmentation_status(self, task_id: str, token: str) -> Dict[str, Any]:
        """
        Check the status of a segmentation task.
        
        Args:
            task_id: Task ID to check
            token: Server token for this task
            
        Returns:
            Dict containing the task status and result URL if complete
        """
        params = {'token': token}
        endpoint = self.settings.status_endpoint.format(task_id=task_id)
        response = self._make_request('GET', endpoint, params=params)
        return response.json()
        
    def download_rtstruct(self, task_id: str, token: str, output_path: str) -> str:
        """
        Download the generated RTSTRUCT file.
        
        Args:
            task_id: Task ID of the completed segmentation
            token: Server token for this task
            output_path: Where to save the RTSTRUCT file
            
        Returns:
            Path to the downloaded file
        """
        params = {'token': token}
        endpoint = self.settings.download_endpoint.format(task_id=task_id)
        response = self._make_request('GET', endpoint, params=params, stream=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        return output_path
        
    def notify_completion(self, task_id: str, token: str, status: str) -> Dict[str, Any]:
        """
        Notify server about RTSTRUCT receipt and processing status.
        
        Args:
            task_id: Task ID of the completed segmentation
            token: Server token for this task
            status: Status update for the server
            
        Returns:
            Dict containing the server's response
        """
        data = {
            'token': token,
            'status': status
        }
        endpoint = self.settings.notify_endpoint.format(task_id=task_id)
        response = self._make_request('POST', endpoint, json=data)
        return response.json()
