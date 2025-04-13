from django.contrib import admin
from dicomapp.models import CopyDicomTaskModel, DicomSeriesProcessingModel, DicomSeriesProcessingLogModel, DicomFileUploadModel
from unfold.admin import ModelAdmin
from unfold.decorators import action
from dicomapp.admin_actions.send_dicom_for_processing import send_dicom_for_processing_action
from dicomapp.admin_actions.upload_dicom_zip import upload_dicom_zip

@admin.register(CopyDicomTaskModel)
class CopyDicomTaskAdmin(ModelAdmin):
    list_display = ('id', 'source_directory', 'target_directory', 'created_at', 'updated_at')
    readonly_fields = ('id', 'source_directory', 'source_directory_creation_date', 
                      'source_directory_modification_date', 'source_directory_size',
                      'target_directory', 'task_id', 'created_at', 'updated_at')
    search_fields = ('source_directory', 'target_directory', 'task_id')
    ordering = ('-created_at',)

@admin.register(DicomSeriesProcessingModel)
class DicomSeriesProcessingAdmin(ModelAdmin):
    list_display = ('patient_id', 'patient_name', 'modality','series_description', 'protocol_name', 'processing_status', 'template_file',
                   'series_state','scan_date' ,'created_at')
    list_editable = ('template_file',)
    readonly_fields = ('id', 'copy_dicom_task_id', 'patient_id', 'patient_name',
                      'gender', 'scan_date', 'modality', 'protocol_name', 'study_instance_uid',
                      'series_instance_uid', 'series_description', 'series_import_directory',
                      'series_archive_directory', 'series_current_directory', 'processing_status', 'series_state',
                      'created_at', 'updated_at')
    search_fields = ('patient_id', 'patient_name', 'modality', 'protocol_name', 'processing_status')
    list_filter = ('processing_status', 'series_state', 'modality','protocol_name','scan_date', 'created_at')
    ordering = ('-created_at',)
    
    actions = [send_dicom_for_processing_action]

@admin.register(DicomSeriesProcessingLogModel)
class DicomSeriesProcessingLogAdmin(ModelAdmin):
    list_display = ('id', 'task_id', 'dicom_series_processing_id', 'processing_status', 
                   'created_at', 'updated_at')
    readonly_fields = ('id', 'task_id', 'dicom_series_processing_id', 'processing_status',
                      'processing_status_message', 'created_at', 'updated_at')
    search_fields = ('task_id', 'processing_status')
    list_filter = ('processing_status',)
    ordering = ('-created_at',)

@admin.register(DicomFileUploadModel)
class DicomFileUploadAdmin(ModelAdmin):
    list_display = ('id', 'file_name', 'unzipped', 'created_at', 'updated_at')
    readonly_fields = ('id', 'file_name', 'unzipped', 'created_at', 'updated_at')
    search_fields = ('file_name',)
    ordering = ('-created_at',)
    actions = [upload_dicom_zip]
