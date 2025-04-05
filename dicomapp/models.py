from django.db import models
import uuid
from dicom_handler.models import ModelYamlInfo, DicomPathConfig
from django.conf import settings
import os
import zipfile
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import re
from pathlib import Path

# Create your models here.

class CopyDicomTaskModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_directory = models.CharField(max_length=512,blank=True,unique=True, help_text="The source directory of the DICOM files")
    source_directory_creation_date = models.DateTimeField(blank=True)
    source_directory_modification_date = models.DateTimeField(blank=True)
    source_directory_size = models.BigIntegerField(blank=True)
    target_directory = models.CharField(max_length=512,blank=True)
    task_id = models.CharField(max_length=255,blank=True, help_text="The task id of the celery task that processed the series")
    copy_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.id}"
    
    class Meta:
        verbose_name = "Copy DICOM Task"
        verbose_name_plural = "Copy DICOM Tasks"
        ordering = ['-created_at']


class ProcessingStatusChoices(models.TextChoices):
    SERIES_SEPARATED = 'SERIES_SEPARATED'
    TEMPLATE_NOT_MATCHED = 'TEMPLATE_NOT_MATCHED'
    MULTIPLE_TEMPLATES_MATCHED = 'MULTIPLE_TEMPLATES_MATCHED'
    MULTIPLE_TEMPLATES_FOUND = 'MULTIPLE_TEMPLATES_FOUND'
    NO_TEMPLATE_FOUND = 'NO_TEMPLATE_FOUND'
    READY_FOR_DEIDENTIFICATION = 'READY_FOR_DEIDENTIFICATION'
    DEIDENTIFIED = 'DEIDENTIFIED'
    DEIDENTIFICATION_FAILED = 'DEIDENTIFICATION_FAILED'
    RTSTRUCT_EXPORT_FAILED = 'RTSTRUCT_EXPORT_FAILED'
    RTSTRUCT_EXPORTED = 'RTSTRUCT_EXPORTED'
    ERROR = 'ERROR'

class SeriesState(models.TextChoices):
    PROCESSING = 'PROCESSING'
    UNPROCESSED = 'UNPROCESSED'
    COMPLETE = 'COMPLETE'
    FAILED = 'FAILED'


class DicomSeriesProcessingModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    copy_dicom_task_id = models.ForeignKey(CopyDicomTaskModel,on_delete=models.CASCADE, null=True, blank=True)
    patient_id = models.CharField(max_length=255,blank=True)
    patient_name = models.CharField(max_length=255,blank=True)
    gender = models.CharField(max_length=10,blank=True)
    scan_date = models.DateField(blank=True)
    modality = models.CharField(max_length=50,blank=True)
    study_instance_uid = models.CharField(max_length=255,blank=True)
    series_instance_uid = models.CharField(max_length=255,blank=True)
    series_description = models.CharField(max_length=255,blank=True)
    series_import_directory = models.CharField(max_length=512,blank=True)
    series_current_directory = models.CharField(max_length=512,blank=True)
    template_file = models.ForeignKey(ModelYamlInfo,on_delete=models.SET_NULL, null=True, blank=True)
    processing_status = models.CharField(max_length=60,blank=True,choices=ProcessingStatusChoices.choices)
    series_state = models.CharField(max_length=60,blank=True,choices=SeriesState.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient_id} - {self.series_instance_uid}"
    
    class Meta:
        verbose_name = "Dicom Series Processing"
        verbose_name_plural = "Dicom Series Processing"
        ordering = ['-created_at']

class DicomSeriesProcessingLogModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_id = models.CharField(max_length=255,blank=True, help_text="The task id of the celery task that processed the series")
    dicom_series_processing_id = models.ForeignKey(DicomSeriesProcessingModel,on_delete=models.CASCADE, null=True, blank=True)
    processing_status = models.CharField(max_length=60,blank=True,choices=ProcessingStatusChoices.choices)
    processing_status_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.id} - {self.dicom_series_processing_id} - {self.processing_status}"
    
    class Meta:
        verbose_name = "Dicom Series Processing Log"
        verbose_name_plural = "Dicom Series Processing Logs"    

class DicomFileUploadModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file_name = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='folders/uploaded_files', blank=True)
    unzipped = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    