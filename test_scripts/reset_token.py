#!/usr/bin/env python
"""
Script to reset the bearer token in the database.
This will clear the existing token so that you can set a new one through the admin interface.
"""

import os
import django
import sys

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'draw_api_client.settings')
django.setup()

from api_client.models import SystemSettings

def reset_token():
    """Reset the bearer token in the database."""
    try:
        settings = SystemSettings.load()
        
        # Clear the token
        settings.encrypted_bearer_token = None
        settings.encrypted_refresh_token = None
        settings.save()
        
        print("Tokens have been cleared successfully.")
        print("Please set a new token through the admin interface at:")
        print("http://localhost:8000/admin/api_client/systemsettings/1/change/")
        
        return True
    except Exception as e:
        print(f"Error resetting token: {str(e)}")
        return False

if __name__ == "__main__":
    print("This script will clear the existing bearer token.")
    print("You will need to set a new token through the admin interface.")
    
    confirm = input("Are you sure you want to continue? (y/n): ")
    if confirm.lower() == 'y':
        success = reset_token()
        if success:
            print("Token reset successful.")
        else:
            print("Token reset failed.")
            sys.exit(1)
    else:
        print("Operation cancelled.")
