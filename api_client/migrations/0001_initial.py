# Generated by Django 5.1.6 on 2025-02-26 16:21

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='APIKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('encrypted_key', models.TextField()),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'API Key',
                'verbose_name_plural': 'API Keys',
            },
        ),
        migrations.CreateModel(
            name='FolderPaths',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('watch_folder', models.CharField(help_text='Directory to monitor for new DICOM files', max_length=512, verbose_name='DICOM Watch Folder')),
                ('temp_folder', models.CharField(help_text='Temporary directory for processing DICOM files', max_length=512, verbose_name='Temporary Folder')),
                ('archive_folder', models.CharField(help_text='Archive directory for processed DICOM files', max_length=512, verbose_name='Archive Folder')),
                ('output_folder', models.CharField(help_text='Output directory for received RTSTRUCT files', max_length=512, verbose_name='Output Folder')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Folder Paths',
                'verbose_name_plural': 'Folder Paths',
            },
        ),
        migrations.CreateModel(
            name='SystemSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_base_url', models.URLField(help_text='Base URL for the DRAW API server', verbose_name='API Base URL')),
                ('client_id', models.CharField(help_text='Unique identifier for this client instance', max_length=200, verbose_name='Client ID')),
                ('encrypted_bearer_token', models.TextField(blank=True, help_text='Encrypted bearer token for API authentication', null=True, verbose_name='Bearer Token')),
                ('encrypted_refresh_token', models.TextField(blank=True, help_text='Encrypted refresh token for API authentication', null=True, verbose_name='Refresh Token')),
                ('token_expiry', models.DateTimeField(blank=True, help_text='Expiration time of the bearer token', null=True, verbose_name='Token Expiry')),
                ('max_retries', models.PositiveIntegerField(default=3, help_text='Maximum number of API request retries', verbose_name='Max Retries')),
                ('upload_endpoint', models.CharField(default='segmentation/upload', help_text='Endpoint for uploading DICOM files', max_length=200, verbose_name='Upload Endpoint')),
                ('status_endpoint', models.CharField(default='segmentation/status/{task_id}', help_text='Endpoint for checking segmentation status. Use {task_id} as placeholder.', max_length=200, verbose_name='Status Endpoint')),
                ('download_endpoint', models.CharField(default='segmentation/download/{task_id}', help_text='Endpoint for downloading RTSTRUCT files. Use {task_id} as placeholder.', max_length=200, verbose_name='Download Endpoint')),
                ('notify_endpoint', models.CharField(default='segmentation/notify/{task_id}', help_text='Endpoint for notifying about RTSTRUCT receipt. Use {task_id} as placeholder.', max_length=200, verbose_name='Notify Endpoint')),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'System Settings',
                'verbose_name_plural': 'System Settings',
            },
        ),
        migrations.CreateModel(
            name='DicomTransfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('study_instance_uid', models.CharField(max_length=255)),
                ('series_instance_uid', models.CharField(max_length=255)),
                ('zip_file_path', models.CharField(max_length=512)),
                ('sent_datetime', models.DateTimeField(blank=True, null=True)),
                ('rtstruct_received_datetime', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('SENT', 'Sent to Server'), ('PROCESSING', 'Processing'), ('COMPLETED', 'RTSTRUCT Received'), ('COMPLETED_NOTIFIED', 'Server Notified'), ('FAILED', 'Failed')], default='PENDING', max_length=20)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('server_task_id', models.CharField(blank=True, max_length=255, null=True)),
                ('server_token', models.CharField(blank=True, max_length=255, null=True)),
                ('rtstruct_file_path', models.CharField(blank=True, max_length=512, null=True)),
                ('cleaned_up', models.BooleanField(default=False)),
                ('last_poll_attempt', models.DateTimeField(blank=True, null=True)),
                ('poll_attempts', models.IntegerField(default=0)),
                ('server_notified', models.BooleanField(default=False)),
                ('zip_checksum', models.CharField(blank=True, help_text='SHA-256 checksum of the zip file', max_length=64, null=True)),
                ('rtstruct_checksum', models.CharField(blank=True, help_text='SHA-256 checksum of the RTSTRUCT file', max_length=64, null=True)),
                ('rtstruct_checksum_verified', models.BooleanField(default=False, help_text='Whether the RTSTRUCT checksum was verified')),
            ],
            options={
                'indexes': [models.Index(fields=['study_instance_uid'], name='api_client__study_i_53a045_idx'), models.Index(fields=['series_instance_uid'], name='api_client__series__7f4a70_idx'), models.Index(fields=['status'], name='api_client__status_7cd984_idx'), models.Index(fields=['cleaned_up'], name='api_client__cleaned_6fbec6_idx'), models.Index(fields=['last_poll_attempt'], name='api_client__last_po_bb1697_idx'), models.Index(fields=['server_notified'], name='api_client__server__2c1411_idx')],
            },
        ),
    ]
