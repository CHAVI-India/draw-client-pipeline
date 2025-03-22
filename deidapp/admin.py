from django.contrib import admin
from deidapp.models import Patient, DicomInstance, DicomSeries, DicomStudy, RTStructFile

from unfold.admin import ModelAdmin
from unfold.decorators import action

# Register your models here.

@admin.register(Patient)
class PatientAdmin(ModelAdmin):
    list_filter = ('patient_id','deidentified_patient_id','patient_name','deidentified_patient_name','patient_birth_date','deidentified_patient_birth_date')
    list_display = ('patient_id','deidentified_patient_id','patient_name','deidentified_patient_name','patient_birth_date','deidentified_patient_birth_date')
    readonly_fields = [field.name for field in Patient._meta.fields]

@admin.register(DicomStudy)
class DicomStudyAdmin(ModelAdmin):
    list_filter = ('patient_id','study_instance_uid','deidentified_study_instance_uid','study_date','deidentified_study_date','study_description')
    list_display = ('patient_id','study_instance_uid','deidentified_study_instance_uid','study_date','deidentified_study_date','study_description')
    readonly_fields = [field.name for field in DicomStudy._meta.fields]

@admin.register(DicomSeries)
class DicomSeriesAdmin(ModelAdmin):
    list_filter = ('study__patient_id','series_date','created_at','updated_at')
    list_display = ('series_instance_uid','study__patient_id','deidentified_series_instance_uid','series_date','deidentified_series_date','frame_of_reference_uid','deidentified_frame_of_reference_uid')
    readonly_fields = [field.name for field in DicomSeries._meta.fields]

@admin.register(DicomInstance)
class DicomInstanceAdmin(ModelAdmin):
    list_filter = ('series__study__patient_id','created_at','updated_at')
    list_display = ('sop_instance_uid','series__study__patient_id','deidentified_sop_instance_uid')
    readonly_fields = [field.name for field in DicomInstance._meta.fields]

@admin.register(RTStructFile)
class RTStructFileAdmin(ModelAdmin):
    list_filter = ('dicom_series__study__patient_id','processing_date','processing_status','created_at','updated_at')
    list_display = ('series_instance_uid','dicom_series__study__patient_id','original_file_path','processed_file_path','processing_date','processing_status')
    readonly_fields = [field.name for field in RTStructFile._meta.fields]

