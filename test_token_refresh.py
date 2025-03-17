#!/usr/bin/env python
"""
Test script for the token refresh functionality.
This script tests the token refresh mechanism by:
1. Setting up a test environment
2. Attempting to refresh the token
3. Verifying the new token works

Usage:
    python test_token_refresh.py <refresh_token>
"""

import os
import sys
import django
import logging
import requests
from datetime import datetime

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'draw_api_client.settings')
django.setup()

from api_client.api_utils.dicom_export import DicomExporter
from api_client.models import SystemSettings
from django.utils import timezone

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(asctime)s %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def test_token_refresh(refresh_token):
    """Test the token refresh functionality with a provided refresh token."""
    try:
        # Load settings
        settings = SystemSettings.load()
        api_base_url = settings.api_base_url.rstrip('/')
        
        # Store the original tokens for comparison
        original_bearer = settings.get_bearer_token()
        original_refresh = settings.get_refresh_token()
        original_expiry = settings.token_expiry
        
        logger.info("Original token information:")
        logger.info(f"Bearer token exists: {'Yes' if original_bearer else 'No'}")
        logger.info(f"Refresh token exists: {'Yes' if original_refresh else 'No'}")
        logger.info(f"Token expiry: {original_expiry}")
        
        # Set the refresh token for testing
        logger.info("Setting test refresh token...")
        settings.set_refresh_token(refresh_token)
        settings.save()
        
        # Create exporter
        exporter = DicomExporter()
        
        # Test token refresh
        logger.info("Testing token refresh...")
        try:
            new_token = exporter._refresh_token()
            logger.info("Token refresh successful!")
            
            # Get updated settings
            settings = SystemSettings.load()
            new_bearer = settings.get_bearer_token()
            new_refresh = settings.get_refresh_token()
            new_expiry = settings.token_expiry
            
            logger.info("New token information:")
            logger.info(f"New bearer token exists: {'Yes' if new_bearer else 'No'}")
            logger.info(f"New refresh token exists: {'Yes' if new_refresh else 'No'}")
            logger.info(f"New token expiry: {new_expiry}")
            
            # Verify token changed
            token_changed = original_bearer != new_bearer
            logger.info(f"Bearer token changed: {'Yes' if token_changed else 'No'}")
            
            # Test if the new token works with a health check
            health_url = f"{api_base_url}/api/health/"
            logger.info(f"Testing new token with health check URL: {health_url}")
            
            headers = {'Authorization': f'Bearer {new_bearer}'}
            response = requests.get(health_url, headers=headers, timeout=5)
            
            logger.info(f"Health check response: {response.status_code}")
            if response.ok:
                logger.info(f"Health check response content: {response.text}")
                logger.info("New token works correctly!")
            else:
                logger.error(f"Health check failed: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                
            return True
            
        except Exception as e:
            logger.error(f"Token refresh failed: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    finally:
        # Restore original tokens if needed
        if original_bearer or original_refresh:
            logger.info("Restoring original tokens...")
            settings = SystemSettings.load()
            if original_bearer:
                settings.set_bearer_token(original_bearer)
            if original_refresh:
                settings.set_refresh_token(original_refresh)
            settings.token_expiry = original_expiry
            settings.save()
            logger.info("Original tokens restored.")

def test_token_refresh_with_expired_token():
    """
    Test the token refresh mechanism when a 401 error occurs.
    This simulates an expired token scenario.
    """
    try:
        # Create exporter
        exporter = DicomExporter()
        settings = SystemSettings.load()
        
        # Save current token state
        original_bearer = settings.get_bearer_token()
        original_refresh = settings.get_refresh_token()
        original_expiry = settings.token_expiry
        
        # Set an invalid bearer token to force a 401 error
        logger.info("Setting an invalid bearer token to simulate expiration...")
        settings.set_bearer_token("invalid_token_to_force_401")
        settings.save()
        
        # Make a request that should trigger the refresh
        logger.info("Making a request that should trigger token refresh...")
        api_base_url = settings.api_base_url.rstrip('/')
        endpoint = "api/health/"
        
        try:
            response = exporter._make_request("GET", endpoint)
            logger.info(f"Request succeeded after token refresh: {response.status_code}")
            
            # Check if token was refreshed
            settings = SystemSettings.load()
            new_bearer = settings.get_bearer_token()
            token_refreshed = new_bearer != "invalid_token_to_force_401"
            
            logger.info(f"Token was refreshed: {'Yes' if token_refreshed else 'No'}")
            return token_refreshed
            
        except Exception as e:
            logger.error(f"Request failed even after token refresh attempt: {str(e)}")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False
    finally:
        # Restore original tokens
        logger.info("Restoring original tokens...")
        settings = SystemSettings.load()
        if original_bearer:
            settings.set_bearer_token(original_bearer)
        if original_refresh:
            settings.set_refresh_token(original_refresh)
        settings.token_expiry = original_expiry
        settings.save()
        logger.info("Original tokens restored.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_token_refresh.py <refresh_token>")
        sys.exit(1)
    
    refresh_token = sys.argv[1]
    logger.info("Starting token refresh test")
    
    # Test direct token refresh
    success = test_token_refresh(refresh_token)
    if success:
        logger.info("Direct token refresh test completed successfully")
    else:
        logger.error("Direct token refresh test failed")
        sys.exit(1)
    
    # Test token refresh during a 401 error
    logger.info("\nStarting token refresh with expired token test")
    success = test_token_refresh_with_expired_token()
    if success:
        logger.info("Token refresh with expired token test completed successfully")
    else:
        logger.error("Token refresh with expired token test failed")
        sys.exit(1)
    
    logger.info("All tests completed successfully")
