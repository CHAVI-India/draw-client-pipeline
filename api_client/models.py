from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from cryptography.fernet import Fernet
import base64
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SystemSettings(models.Model):
    """
    Singleton model for system settings.
    Contains all the configurable settings for the DRAW API client.
    """
    
    api_base_url = models.URLField(
        verbose_name="API Base URL",
        help_text="Base URL for the DRAW API server"
    )
    client_id = models.CharField(
        verbose_name="Client ID",
        max_length=200,
        help_text="Unique identifier for this client instance"
    )
    encrypted_bearer_token = models.TextField(
        verbose_name="Bearer Token",
        null=True,
        blank=True,
        help_text="Encrypted bearer token for API authentication"
    )
    encrypted_refresh_token = models.TextField(
        verbose_name="Refresh Token",
        null=True,
        blank=True,
        help_text="Encrypted refresh token for API authentication"
    )
    token_expiry = models.DateTimeField(
        verbose_name="Token Expiry",
        null=True,
        blank=True,
        help_text="Expiration time of the bearer token"
    )
    max_retries = models.PositiveIntegerField(
        verbose_name="Max Retries",
        default=3,
        help_text="Maximum number of API request retries"
    )
    # API endpoint patterns
    upload_endpoint = models.CharField(
        verbose_name="Upload Endpoint",
        max_length=200,
        default='api/upload/',
        help_text="Endpoint for uploading DICOM files. IMPORTANT: The trailing slash is required."
    )
    status_endpoint = models.CharField(
        verbose_name="Status Endpoint",
        max_length=200,
        default='api/upload/{task_id}/status/',
        help_text="Endpoint for checking segmentation status. Use {task_id} as placeholder for the transaction ID provided by the server. IMPORTANT: The trailing slash is required."
    )
    download_endpoint = models.CharField(
        verbose_name="Download Endpoint",
        max_length=200,
        default='api/rtstruct/{task_id}/',
        help_text="Endpoint for downloading RTSTRUCT files. Use {task_id} as placeholder for the transaction ID provided by the server. IMPORTANT: The trailing slash is required."
    )
    notify_endpoint = models.CharField(
        verbose_name="Notify Endpoint",
        max_length=200,
        default='api/rtstruct/{task_id}/confirm/',
        help_text="Endpoint for notifying about RTSTRUCT receipt. Use {task_id} as placeholder for the transaction ID provided by the server. IMPORTANT: The trailing slash is required."
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"
    
    def save(self, *args, **kwargs):
        self.pk = 1
        
        # Encrypt tokens if they are being set/changed
        if hasattr(self, '_bearer_token'):
            self.encrypted_bearer_token = self.encrypt_value(self._bearer_token)
            del self._bearer_token
            
        if hasattr(self, '_refresh_token'):
            self.encrypted_refresh_token = self.encrypt_value(self._refresh_token)
            del self._refresh_token
            
        super().save(*args, **kwargs)
    
    @staticmethod
    def get_encryption_key():
        """Generate a Fernet key from Django's SECRET_KEY."""
        key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32].ljust(32, b'\0'))
        return key
    
    def encrypt_value(self, value):
        """Encrypt a value using Fernet."""
        if value is None:
            return None
        try:
            f = Fernet(self.get_encryption_key())
            return f.encrypt(value.encode()).decode()
        except Exception as e:
            print(f"Error encrypting value: {type(e).__name__}: {str(e)}")
            raise
    
    def decrypt_value(self, encrypted_value):
        """Decrypt a stored value."""
        if encrypted_value is None:
            return None
        try:
            f = Fernet(self.get_encryption_key())
            return f.decrypt(encrypted_value.encode()).decode()
        except Exception as e:
            print(f"Error decrypting value: {type(e).__name__}: {str(e)}")
            print(f"This may indicate that the value was stored without encryption.")
            print(f"Try clearing the token in the admin interface and setting it again.")
            # Return the encrypted value as-is for debugging
            return encrypted_value
        
    def set_bearer_token(self, token):
        """Set the bearer token - it will be encrypted on save."""
        self._bearer_token = token
        
    def set_refresh_token(self, token):
        """Set the refresh token - it will be encrypted on save."""
        self._refresh_token = token
        
    def get_bearer_token(self):
        """Get the decrypted bearer token."""
        return self.decrypt_value(self.encrypted_bearer_token)
        
    def get_refresh_token(self):
        """Get the decrypted refresh token."""
        return self.decrypt_value(self.encrypted_refresh_token)
        
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
    
    def __str__(self):
        return "System Settings"

# class FolderPaths(models.Model):
#     """
#     Singleton model for folder path configurations.
#     All paths are relative to the project's base directory and will be created if they don't exist.
#     """
#     watch_folder = models.CharField(
#         max_length=512,
#         verbose_name="DICOM Watch Folder",
#         default='processed_dicom',
#         help_text="Directory to monitor for new DICOM files (relative to base directory)"
#     )
#     temp_folder = models.CharField(
#         max_length=512,
#         verbose_name="Temporary Folder",
#         default='temporary',
#         help_text="Temporary directory for processing DICOM files (relative to base directory)"
#     )
#     archive_folder = models.CharField(
#         max_length=512,
#         verbose_name="Archive Folder",
#         default='archive',
#         help_text="Archive directory for processed DICOM files (relative to base directory)"
#     )
#     output_folder = models.CharField(
#         max_length=512,
#         verbose_name="Output Folder",
#         default='rtstruct',
#         help_text="Output directory for received RTSTRUCT files (relative to base directory)"
#     )
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = "Folder Paths"
#         verbose_name_plural = "Folder Paths"
    
#     def get_absolute_path(self, relative_path):
#         """Convert a relative path to an absolute path based on the project's base directory."""
#         return Path(settings.BASE_DIR) / relative_path
    
#     def get_watch_folder_path(self):
#         """Get the absolute path for the watch folder."""
#         return self.get_absolute_path(self.watch_folder)
    
#     def get_temp_folder_path(self):
#         """Get the absolute path for the temporary folder."""
#         return self.get_absolute_path(self.temp_folder)
    
#     def get_archive_folder_path(self):
#         """Get the absolute path for the archive folder."""
#         return self.get_absolute_path(self.archive_folder)
    
#     def get_output_folder_path(self):
#         """Get the absolute path for the output folder."""
#         return self.get_absolute_path(self.output_folder)
    
#     def save(self, *args, **kwargs):
#         self.pk = 1
#         # Create directories if they don't exist
#         for field in ['watch_folder', 'temp_folder', 'archive_folder', 'output_folder']:
#             path = self.get_absolute_path(getattr(self, field))
#             try:
#                 os.makedirs(path, exist_ok=True)
#             except Exception as e:
#                 raise ValidationError({field: f"Could not create directory: {str(e)}"})
#         super().save(*args, **kwargs)
    
#     @classmethod
#     def load(cls):
#         obj, created = cls.objects.get_or_create(pk=1)
#         return obj
    
#     def __str__(self):
#         return "Folder Paths"

class DicomTransfer(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent to Server'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'RTSTRUCT Received'),
        ('COMPLETED_NOTIFIED', 'Server Notified'),
        ('FAILED', 'Failed'),
    ]

    study_instance_uid = models.CharField(max_length=255)
    series_instance_uid = models.CharField(max_length=255)
    zip_file_path = models.CharField(
        max_length=512,
        help_text="Path to the zip file (relative to base directory)"
    )
    sent_datetime = models.DateTimeField(null=True, blank=True)
    rtstruct_received_datetime = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    server_task_id = models.CharField(max_length=255, null=True, blank=True)
    server_token = models.CharField(max_length=255, null=True, blank=True)
    server_status = models.CharField(max_length=255, null=True, blank=True, help_text="Status reported by the server")
    rtstruct_file_path = models.CharField(
        max_length=512,
        null=True,
        blank=True,
        help_text="Path to the RTSTRUCT file (relative to base directory)"
    )
    cleaned_up = models.BooleanField(default=False)
    last_poll_attempt = models.DateTimeField(null=True, blank=True)
    poll_attempts = models.IntegerField(default=0)
    server_notified = models.BooleanField(default=False)
    zip_checksum = models.CharField(max_length=64, null=True, blank=True, help_text="SHA-256 checksum of the zip file")
    rtstruct_checksum = models.CharField(max_length=64, null=True, blank=True, help_text="SHA-256 checksum of the RTSTRUCT file")
    rtstruct_checksum_verified = models.BooleanField(default=False, help_text="Whether the RTSTRUCT checksum was verified")

    class Meta:
        indexes = [
            models.Index(fields=['study_instance_uid']),
            models.Index(fields=['series_instance_uid']),
            models.Index(fields=['status']),
            models.Index(fields=['cleaned_up']),
            models.Index(fields=['last_poll_attempt']),
            models.Index(fields=['server_notified']),
        ]

    def __str__(self):
        return f"Transfer {self.id} - Study: {self.study_instance_uid} - Status: {self.status}"

    def get_absolute_path(self, relative_path):
        """Convert a relative path to an absolute path based on the project's base directory."""
        if not relative_path:
            return None
        return Path(settings.BASE_DIR) / relative_path

    def get_zip_file_path(self):
        """Get the absolute path for the zip file."""
        return self.get_absolute_path(self.zip_file_path)

    def get_rtstruct_file_path(self):
        """Get the absolute path for the RTSTRUCT file."""
        return self.get_absolute_path(self.rtstruct_file_path)

    def mark_as_sent(self):
        self.sent_datetime = timezone.now()
        self.status = 'SENT'
        self.save()

    def mark_as_completed(self, rtstruct_path):
        self.rtstruct_received_datetime = timezone.now()
        self.status = 'COMPLETED'
        # Convert absolute path to relative path before saving
        try:
            rtstruct_path = Path(rtstruct_path)
            self.rtstruct_file_path = str(rtstruct_path.relative_to(settings.BASE_DIR))
        except ValueError:
            # If the path is not relative to BASE_DIR, store it as-is
            self.rtstruct_file_path = str(rtstruct_path)
        self.save()

    def mark_as_notified(self):
        self.status = 'COMPLETED_NOTIFIED'
        self.server_notified = True
        self.save()

    def mark_as_failed(self, error_message):
        self.status = 'FAILED'
        self.error_message = error_message
        self.save()

    def update_poll_attempt(self):
        """Update polling attempt information."""
        self.last_poll_attempt = timezone.now()
        self.poll_attempts += 1
        self.save(update_fields=['last_poll_attempt', 'poll_attempts'])

    def update_status(self, status):
        """Update the status of the transfer.
        
        This method is used to update the status of a transfer when it's
        in an intermediate state like 'PROCESSING'.
        """
        if status in [s[0] for s in self.STATUS_CHOICES]:
            self.status = status
            self.save(update_fields=['status', 'updated_at'])
        else:
            # Log but don't raise an exception for unknown status
            logger.warning(f"Attempted to update transfer {self.id} with unknown status: {status}")

    def update_server_status(self, server_status):
        """Update the server_status field with the status reported by the server.
        
        This method keeps track of the server-side status separately from the
        client-side status.
        """
        self.server_status = server_status
        self.save(update_fields=['server_status', 'updated_at'])
        logger.info(f"Updated server status for transfer {self.id} to: {server_status}")
