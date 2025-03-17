#!/usr/bin/env python
"""
Test script for the health check endpoint.
This bypasses the token encryption/decryption process by setting the token directly.
"""

import os
import sys
import django
import logging
import requests

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'draw_api_client.settings')
django.setup()

from api_client.api_utils.dicom_export import DicomExporter
from api_client.models import SystemSettings

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_health_check_with_token(token):
    """Test the health check endpoint with a manually set token."""
    try:
        # Create exporter and set test token
        exporter = DicomExporter()
        exporter.set_test_token(token)
        
        # Get settings
        settings = SystemSettings.load()
        api_base_url = settings.api_base_url.rstrip('/')
        
        # Test direct access to the API base URL
        logger.info(f"Testing direct access to API base URL: {api_base_url}")
        try:
            response = requests.get(api_base_url, timeout=5)
            logger.info(f"API base URL response: {response.status_code}")
        except Exception as e:
            logger.error(f"Error accessing API base URL: {str(e)}")
        
        # Test health check URL directly
        health_url = f"{api_base_url}/api/health/"
        logger.info(f"Testing direct access to health check URL: {health_url}")
        try:
            response = requests.get(health_url, timeout=5)
            logger.info(f"Health check URL direct response: {response.status_code}")
            if response.ok:
                logger.info(f"Health check direct response content: {response.text}")
        except Exception as e:
            logger.error(f"Error accessing health check URL directly: {str(e)}")
        
        # Test health check with authentication
        logger.info(f"Testing health check with authentication")
        headers = exporter._get_headers()
        try:
            response = requests.get(health_url, headers=headers, timeout=5)
            logger.info(f"Health check with auth response: {response.status_code}")
            if response.ok:
                logger.info(f"Health check with auth response content: {response.text}")
            else:
                logger.error(f"Health check with auth failed: {response.status_code}")
                logger.error(f"Response content: {response.text}")
        except Exception as e:
            logger.error(f"Error during health check with auth: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_health_check.py <bearer_token>")
        sys.exit(1)
    
    token = sys.argv[1]
    logger.info("Starting health check test")
    success = test_health_check_with_token(token)
    if success:
        logger.info("Test completed")
    else:
        logger.error("Test failed")
        sys.exit(1)
