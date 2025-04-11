# Register your models here.
import os
import zipfile
import logging
from django.contrib import admin
from django.contrib import messages
from dicom_handler.models import *
# from dicom_handler.dicomutils.unprocesstoprocessing import move_folder_with_yaml_check
# from dicom_handler.dicomutils.dicomseriesprocessing import read_dicom_metadata, dicom_series_separation
# from dicom_handler.dicomutils.manual_dicom_zip_processing import send_to_autosegmentation
# from dicom_handler.dicomutils.move_from_unprocessed_to_processing import move_from_unprocessed_to_processing
from django.conf import settings
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import action
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from django_celery_beat.models import (
    ClockedSchedule,
    CrontabSchedule,
    IntervalSchedule,
    PeriodicTask,
    SolarSchedule,
)

from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget
from allauth.account.decorators import secure_admin_login
from django_celery_beat.admin import ClockedScheduleAdmin as BaseClockedScheduleAdmin
from django_celery_beat.admin import CrontabScheduleAdmin as BaseCrontabScheduleAdmin
from django_celery_beat.admin import PeriodicTaskAdmin as BasePeriodicTaskAdmin
from django_celery_beat.admin import PeriodicTaskForm, TaskSelectWidget

admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(SolarSchedule)
admin.site.unregister(ClockedSchedule)

class UnfoldTaskSelectWidget(UnfoldAdminSelectWidget, TaskSelectWidget):
    pass

class UnfoldPeriodicTaskForm(PeriodicTaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["task"].widget = UnfoldAdminTextInputWidget()
        self.fields["regtask"].widget = UnfoldTaskSelectWidget()


@admin.register(PeriodicTask)
class PeriodicTaskAdmin(BasePeriodicTaskAdmin, ModelAdmin):
    form = UnfoldPeriodicTaskForm


@admin.register(IntervalSchedule)
class IntervalScheduleAdmin(ModelAdmin):
    pass


@admin.register(CrontabSchedule)
class CrontabScheduleAdmin(BaseCrontabScheduleAdmin, ModelAdmin):
    pass


@admin.register(SolarSchedule)
class SolarScheduleAdmin(ModelAdmin):
    pass

@admin.register(ClockedSchedule)
class ClockedScheduleAdmin(BaseClockedScheduleAdmin, ModelAdmin):
    pass

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)


admin.site.unregister(User)
admin.site.unregister(Group)

logger = logging.getLogger('dicom_handler_logs')
@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass



@admin.register(DicomPathConfig)
class DicomPathConfigAdmin(ModelAdmin):
    list_display = ('datastorepath', 'date_time_to_start_pulling_data')

# Function to get DicomPathConfig values when needed, not at module import time
def get_dicom_path_config():
    try:
        import_dir = os.path.join(settings.BASE_DIR, 'folder_for_dicom_import')
        deidentified_dir = os.path.join(settings.BASE_DIR, 'folder_for_deidentification')
        unprocessed_dir = os.path.join(settings.BASE_DIR, 'folder_unprocessed_dicom')
        processing_dir = os.path.join(settings.BASE_DIR, 'folder_dicom_processing')

        # Create the deidentified, unprocessed and processing folder if they don't exist
        os.makedirs(import_dir, exist_ok=True)
        os.makedirs(deidentified_dir, exist_ok=True)
        os.makedirs(unprocessed_dir, exist_ok=True)
        os.makedirs(processing_dir, exist_ok=True)

        return import_dir, deidentified_dir, unprocessed_dir, processing_dir   
    except Exception as e:
        logger.error(f"DicomPathConfig error: {str(e)}")
        # Create default directories even if DicomPathConfig is not set
        import_dir = os.path.join(settings.BASE_DIR, 'folder_for_dicom_import')
        deidentified_dir = os.path.join(settings.BASE_DIR, 'folder_for_deidentification')
        unprocessed_dir = os.path.join(settings.BASE_DIR, 'folder_unprocessed_dicom')
        processing_dir = os.path.join(settings.BASE_DIR, 'folder_dicom_processing')
        
        # Create the directories if they don't exist
        os.makedirs(import_dir, exist_ok=True)
        os.makedirs(deidentified_dir, exist_ok=True)
        os.makedirs(unprocessed_dir, exist_ok=True)
        os.makedirs(processing_dir, exist_ok=True)
        
        # Use a default import directory
        import_dir = os.path.join(settings.BASE_DIR, 'folder_for_dicom_import')
        os.makedirs(import_dir, exist_ok=True)
        
        logger.warning(f"Using default DicomPathConfig paths: {import_dir}")
        return import_dir, deidentified_dir, unprocessed_dir, processing_dir
   

class ModelYamlInfoAdmin(ModelAdmin):
    list_display = (
        'yaml_name', 
        'protocol', 
        'yaml_description',
        'get_rule_set_name',
        'created_at',
    )
    readonly_fields = [
        'yaml_name',
        'yaml_path',
        'protocol',
        'file_hash',
        'yaml_description',
        'created_at',
        'modified_at',
    ]
    search_fields = ('yaml_name','protocol','yaml_description')
    search_help_text = "Search by YAML name, protocol, or description"
    list_filter = ('yaml_name', 'protocol','created_at',)
    list_per_page = 10

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('ruleset')

    @admin.display(description='Rule Set')
    def get_rule_set_name(self, obj):
        return obj.ruleset.rule_set_name if hasattr(obj, 'ruleset') else '-'

admin.site.register(ModelYamlInfo, ModelYamlInfoAdmin)

# Rule admin
class RuleAdmin(ModelAdmin):
    list_display = (
        "rule_set",
        "tag_name",
        "tag_value",
        "created_at",
        "modified_at",

    )
    list_per_page = 14
    search_fields = ('rule_set','tag_name','tag_value')
    list_filter = ('rule_set','tag_name','tag_value')

admin.site.register(Rule, RuleAdmin)

# RuleSet admin
class RuleInline(TabularInline):
    model = Rule
    extra = 1
    autocomplete_fields = ['tag_name']
    
class RuleSetAdmin(ModelAdmin):
    inlines = [RuleInline]
    list_display = (
        "rule_set_name",
        "description",
        "model_yaml",
        "created_at",
        "modified_at",
    )
    ordering = ('rule_set_name',)
    list_per_page = 14
    search_fields = ('rule_set_name', "description", "model_yaml", "created_at")
    list_filter = ('rule_set_name', "model_yaml", "created_at")
   

admin.site.register(RuleSet, RuleSetAdmin)

# Tagname admin
class TagnameAdmin(ModelAdmin):
    search_fields = ('tag_id', 'tag_name', 'tag_description', 'value_representation')
    list_display = ('tag_id', 'tag_name', 'tag_description', 'value_representation')
    ordering = ('tag_name',)
    list_per_page = 14

admin.site.register(TagName, TagnameAdmin)


# @admin.register(DicomSeriesProcessing)
# class DicomSeriesProcessingAdmin(ModelAdmin):
#     list_display = ('patientid', 'patientname', 'gender', 'studyid', 'seriesid', 'studydate', 'modality', 'protocol', 'description', 'dicomcount', 'series_split_done', 'processing_start', 'processing_end', 'created_at', 'modified_at')
#     search_fields = ('patientid', 'patientname', 'gender', 'studyid', 'seriesid', 'studydate', 'modality', 'protocol', 'description', 'dicomcount', 'series_split_done', 'processing_start', 'processing_end', 'created_at', 'modified_at')
#     list_filter = ('patientid', 'patientname', 'gender', 'studyid', 'seriesid', 'studydate', 'modality', 'protocol', 'description', 'dicomcount', 'series_split_done', 'processing_start', 'processing_end', 'created_at', 'modified_at')

#     def get_readonly_fields(self, request, obj=None):
#         # Make all fields readonly
#         if obj:  # Only apply when editing an existing object
#             return [f.name for f in self.model._meta.fields]
#         return []


# class uploadDicomAdmin(ModelAdmin):
#     list_display = (
#         'id', 
#         'dicom_file',
#         'send_to_autosegmentation',
#         'created_at',
#         'modified_at'
#     )

#     list_filter = ('send_to_autosegmentation','created_at',)
#     exclude = ('send_to_autosegmentation',)
#     search_fields = ('dicom_file',)
#     actions = [send_to_autosegmentation]
#     list_per_page = 10

# admin.site.register(uploadDicom, uploadDicomAdmin)

# class CopyDicomAdmin(ModelAdmin):
#     list_display = (
#         "sourcedirname",
#         "destinationdirname",
#         "dirsize",
#         "processing_status",
#         "dirmodifieddate",
#         "dircreateddate",
#         "copydate",
#     )
#     list_per_page = 14
#     search_fields = ('sourcedirname', 'destinationdirname')
#     list_filter = ('copydate',
#                    'dirmodifieddate',
#                    'dircreateddate',
#                    'processing_status',
#                    )
#     def get_readonly_fields(self, request, obj=None):
#         # Make all fields readonly
#         if obj:  # Only apply when editing an existing object
#             return [f.name for f in self.model._meta.fields]
#         return []

# admin.site.register(CopyDicom, CopyDicomAdmin)


# class MyModelAdmin(ModelAdmin):
#     # Override get_queryset to ensure only one record exists
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         if qs.count() > 1:
#             # Optionally, you can add a validation or a message here
#             raise Exception("Only one record is allowed in the database.")
#         return qs

#     # Restrict adding new records (only allow if there's no record yet)
#     def has_add_permission(self, request):
#         if DicomImportConfig.objects.count() >= 1:
#             return False  # Prevent adding more than one record
#         return True

# admin.site.register(DicomImportConfig, MyModelAdmin)




# @admin.action(description="Send to processing")
# def send_to_processing(modeladmin, request, queryset):
#     # Get DicomPathConfig values when the action is executed
#     import_dir, deidentified_dir, unprocessed_dir, processing_dir = get_dicom_path_config()
#     if not all([import_dir, deidentified_dir, unprocessed_dir, processing_dir]):
#         messages.error(request, "DicomPathConfig not set properly")
#         return
    
#     for obj in queryset:
#         try:

#             move_folder_with_yaml_check(
#                 unprocess_dir=obj.series_folder_location,
#                 copy_yaml=obj.yaml_attached.yaml_path
#             )
#             logger.info(f"Successfully moved {obj.series_folder_location} to processing")
           
#             instance = DicomUnprocessed.objects.get(id=obj.id)
#             logger.info(f"Successfully updated {instance.id} to unprocessed")
#             instance.unprocessed = False
#             instance.series_folder_location = os.path.join(
#                 processing_dir, os.path.basename(obj.series_folder_location)
#             )
#             instance.save()
#             logger.info(f"Successfully updated {instance.id} to unprocessed")

#             read_dicom_metadata(
#                 dicom_series_path = os.path.join(
#                     processing_dir,
#                     os.path.basename(obj.series_folder_location)
#                 ),
#                 unprocess_dicom_path = os.path.join(
#                     unprocessed_dir,
#                     os.path.basename(obj.series_folder_location)
#                 ),
#                 deidentified_dicom_path = os.path.join(
#                     deidentified_dir,
#                     os.path.basename(obj.series_folder_location)
#                 )
#             )
            
#             messages.success(request, f"Successfully sent {obj.patientid} to processing")
           

#         except Exception as e:
#             instance = DicomUnprocessed.objects.get(id=obj.id)
#             instance.unprocessed = True
#             instance.save()
#             logger.info(f"Successfully updated {instance.id} to unprocessed")
#             messages.error(request, f"Error sending {obj.patientid} to processing")
#             print(e)


# dicom unprocess admin
# class UnprocessedAdmin(ModelAdmin):
#     list_display = (
#         'patientid', 
#         'patientname',
#         'gender',
#         'yaml_attached',
#         'ready_for_deidentification',
#         'studydate',
#         'modality',
#         'protocol',
#         'description'
#     )

#     readonly_fields = ['patientid', 
#         'patientname',
#         'gender',
#         'studyid',
#         'seriesid', 
#         'studydate',
#         'modality',
#         'protocol',
#         'description',
#         'processing_start',
#         'processing_end',
#         'dicomcount',
#         'ready_for_deidentification',
#         'unprocessed',
#         'series_folder_location']
    
#     list_editable = ['yaml_attached',]
#     list_filter = ('unprocessed', 'ready_for_deidentification','modality','protocol','studydate')
#     search_fields = ('patientid',)
#     actions = [move_from_unprocessed_to_processing]
#     list_per_page = 10

#     # def get_queryset(self, request):
#     #     return super().get_queryset(request).filter(unprocessed=True)

# admin.site.register(DicomUnprocessed, UnprocessedAdmin)



# dicom processed admin
# class ProcessingStatusAdmin(ModelAdmin):
#     list_display = (
#         'patient_id',
#         'patient_name',
#         'patient_gender',
#         'patient_modality',
#         'patient_protocol',
#         'patient_description',
#         'status',
#         'dicom_move_folder_status',
#         'created_at',
#     )
#     list_filter = (
#         'dicom_move_folder_status',
#         'yaml_attach_status', 
#         'patient_id__modality',
#         'patient_id__studydate',
#         'created_at'
#     )
#     search_fields = (
#         'patient_id__patientid', 
#         'patient_id__patientname',
#         'patient_id__protocol',
#         'patient_id__description',
#     )
#     list_select_related = ('patient_id',)
#     list_per_page = 10
#     search_help_text = "Search by patient ID, patient name, protocol, or description"
#     def get_readonly_fields(self, request, obj=None):
#         # Make all fields readonly
#         if obj:  # Only apply when editing an existing object
#             return [f.name for f in self.model._meta.fields]
#         return []

#     @admin.display(description='Patient Name')
#     def patient_name(self, obj):
#         return obj.patient_id.patientname
    
#     @admin.display(description='Gender')
#     def patient_gender(self, obj):
#         return obj.patient_id.gender

#     @admin.display(description='Modality')
#     def patient_modality(self, obj):
#         return obj.patient_id.modality

#     @admin.display(description='Protocol')
#     def patient_protocol(self, obj):
#         return obj.patient_id.protocol

#     @admin.display(description='Description')
#     def patient_description(self, obj):
#         return obj.patient_id.description

# admin.site.register(ProcessingStatus, ProcessingStatusAdmin)