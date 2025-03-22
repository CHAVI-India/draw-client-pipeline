from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import DicomTransfer, SystemSettings, FolderPaths
from django.contrib import messages
from django import forms
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import *
from unfold.decorators import action



class SystemSettingsForm(forms.ModelForm):
    bearer_token = forms.CharField(
        label="Bearer Token",
        widget=forms.Textarea,
        required=False,
        help_text="Enter the bearer token for API authentication. It will be encrypted when saved."
    )
    
    refresh_token = forms.CharField(
        label="Refresh Token",
        widget=forms.Textarea,
        required=False,
        help_text="Enter the refresh token for API authentication. It will be encrypted when saved."
    )
    
    class Meta:
        model = SystemSettings

        fieldsets = (
            ('API Configuration', {
                'fields': ('api_base_url', 'client_id', 'max_retries'),
                'description': 'Configure the connection to the DRAW API server'
            }),
            ('API Endpoints', {
                'fields': ('upload_endpoint', 'status_endpoint', 'download_endpoint', 'notify_endpoint'),
                'description': 'Configure the API endpoints'
            }),
            ('Authentication', {
                'fields': ('bearer_token', 'refresh_token', 'token_expiry'),
                'description': 'Configure authentication tokens. These will be encrypted when saved.'
            }),
        )

        # fields = [
        #     'api_base_url', 'client_id', 'max_retries',
        #     'upload_endpoint', 'status_endpoint', 'download_endpoint', 'notify_endpoint',
        #     'bearer_token', 'refresh_token', 'token_expiry'
        # ]
        exclude = ['encrypted_bearer_token', 'encrypted_refresh_token','updated_at']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't show the current token values for security
        if self.instance.pk:
            self.fields['bearer_token'].initial = ''
            self.fields['refresh_token'].initial = ''
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set tokens if provided
        if self.cleaned_data.get('bearer_token'):
            instance.set_bearer_token(self.cleaned_data['bearer_token'])
        
        if self.cleaned_data.get('refresh_token'):
            instance.set_refresh_token(self.cleaned_data['refresh_token'])
        
        if commit:
            instance.save()
        
        return instance

@admin.register(SystemSettings)
class SystemSettingsAdmin(ModelAdmin):
    form = SystemSettingsForm
    list_display = ['api_base_url', 'max_retries', 'updated_at']
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('API Configuration', {
            'fields': ('api_base_url', 'client_id', 'max_retries'),
            'description': 'Configure the connection to the DRAW API server'
        }),
        ('API Endpoints', {
            'fields': ('upload_endpoint', 'status_endpoint', 'download_endpoint', 'notify_endpoint'),
            'description': 'Configure the API endpoints'
        }),
        ('Authentication', {
            'fields': ('bearer_token', 'refresh_token', 'token_expiry'),
            'description': 'Configure authentication tokens. These will be encrypted when saved.'
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        return not SystemSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the singleton instance
        return False

@admin.register(FolderPaths)
class FolderPathsAdmin(ModelAdmin):
    list_display = ['watch_folder', 'temp_folder', 'archive_folder', 'output_folder', 'updated_at']
    readonly_fields = ['updated_at']
    
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        return not FolderPaths.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of the singleton instance
        return False

@admin.register(DicomTransfer)
class DicomTransferAdmin(ModelAdmin):
    list_display = [
        'id', 'study_instance_uid', 'status','server_status', 'sent_datetime', 
        'rtstruct_received_datetime', 'rtstruct_checksum_verified'
    ]
    
    list_filter = ['status', 'rtstruct_checksum_verified']
    search_fields = ['study_instance_uid', 'series_instance_uid', 'error_message', 'zip_checksum', 'rtstruct_checksum']
    
    # Make all fields read-only since processing is automatic
    readonly_fields = [
        'study_instance_uid', 'series_instance_uid', 'zip_file_path',  'server_token',
        'status', 'error_message',
        'rtstruct_file_path',
        'sent_datetime', 'rtstruct_received_datetime',
        'cleaned_up', 'last_poll_attempt', 'poll_attempts', 'server_notified',
        'created_at', 'updated_at',
        'zip_checksum', 'rtstruct_checksum', 'rtstruct_checksum_verified',
        'server_status'
    ]

    fieldsets = (
        ('Transfer Information', {
            'fields': (
                'study_instance_uid', 'series_instance_uid', 'zip_file_path', 'zip_checksum', 'server_token'
            ),
            'description': 'The server_token fields both contain the transaction token from the server.'
        }),
        ('Status', {
            'fields': ('status', 'error_message', 'rtstruct_file_path', 'server_status')
        }),
        ('RTSTRUCT Verification', {
            'fields': ('rtstruct_checksum', 'rtstruct_checksum_verified'),
            'description': 'Checksum verification status for received RTSTRUCT file'
        }),
        ('Timestamps', {
            'fields': ('sent_datetime', 'rtstruct_received_datetime', 'created_at', 'updated_at')
        }),
        ('Processing Info', {
            'fields': ('cleaned_up', 'last_poll_attempt', 'poll_attempts', 'server_notified'),
            'classes': ('collapse',)
        })
    )
