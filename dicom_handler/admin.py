
# Register your models here.
import os
import zipfile
from django.contrib import admin
from django.contrib import messages
from solo.admin import SingletonModelAdmin
from .models import DicomPathConfig, DicomImportConfig, DicomUnprocessed, ProcessingStatus, ModelYamlInfo
from .models import Rule, RuleSet, TagName, uploadDicom, CopyDicom
from dicom_handler.dicomutils.unprocesstoprocessing import move_folder_with_yaml_check
from dicom_handler.dicomutils.dicomseriesprocessing import read_dicom_metadata, dicom_series_separation

from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group
from unfold.admin import ModelAdmin
from unfold.decorators import action
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from allauth.account.decorators import secure_admin_login

admin.autodiscover()
admin.site.login = secure_admin_login(admin.site.login)


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


# Unprocessed
try:
    import_dir = DicomPathConfig.objects.values("dicomimportfolderpath").first()["dicomimportfolderpath"]
    processing_dir = DicomPathConfig.objects.values("dicomprocessingfolderpath").first()
    unprocessed_dir = DicomPathConfig.objects.values("dicomnonprocessedfolderpath").first()
    deidentified_dir = DicomPathConfig.objects.values("deidentificationfolderpath").first()
except:
    print("DicomPathConfig not set")
    
   
admin.site.register(DicomPathConfig, SingletonModelAdmin)


class MyModelAdmin(ModelAdmin):
    # Override get_queryset to ensure only one record exists
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if qs.count() > 1:
            # Optionally, you can add a validation or a message here
            raise Exception("Only one record is allowed in the database.")
        return qs

    # Restrict adding new records (only allow if there's no record yet)
    def has_add_permission(self, request):
        if DicomImportConfig.objects.count() >= 1:
            return False  # Prevent adding more than one record
        return True

admin.site.register(DicomImportConfig, MyModelAdmin)




@admin.action(description="Send to processing")
def send_to_processing(modeladmin, request, queryset):

    for obj in queryset:
        try:
            print("#######")
            # print(ModelYamlInfo.objects.filter(id = obj.yaml_attached))
            print(obj.yaml_attached.yaml_path)
            print(obj.series_folder_location)
            print("-" * 50)

            move_folder_with_yaml_check(
                unprocess_dir=obj.series_folder_location,
                copy_yaml=obj.yaml_attached.yaml_path
            )
           
            instance = DicomUnprocessed.objects.get(id=obj.id)
            instance.unprocessed = False
            instance.series_folder_location = os.path.join(
                processing_dir, os.path.basename(obj.series_folder_location)
            )
            instance.save()

            read_dicom_metadata(
                dicom_series_path = os.path.join(
                    processing_dir,
                    os.path.basename(obj.series_folder_location)
                ),
                unprocess_dicom_path = os.path.join(
                    unprocessed_dir,
                    os.path.basename(obj.series_folder_location)
                ),
                deidentified_dicom_path = os.path.join(
                    deidentified_dir,
                    os.path.basename(obj.series_folder_location)
                )
            )
            
            messages.success(request, f"Successfully sent {obj.patientid} to processing")
           

        except Exception as e:
            instance = DicomUnprocessed.objects.get(id=obj.id)
            instance.unprocessed = True
            instance.save()
            
            messages.error(request, f"Error sending {obj.patientid} to processing")
            print(e)


# dicom unprocess admin
class UnprocessedAdmin(ModelAdmin):
    list_display = (
        'patientid', 
        'patientname',
        'gender',
        'yaml_attached',
        'studydate',
        'modality',
        'protocol',
        'description'
    )

    readonly_fields = ['patientid', 
        'patientname',
        'gender',
        'studyid',
        'seriesid', 
        'studydate',
        'modality',
        'protocol',
        'description',
        'processing_start',
        'processing_end',
        'dicomcount',
        'series_folder_location']
    
    list_editable = ['yaml_attached',]
    list_filter = ('studydate',)
    search_fields = ('patientid',)
    actions = [send_to_processing]
    list_per_page = 10

    def get_queryset(self, request):
        return super().get_queryset(request).filter(unprocessed=True)

admin.site.register(DicomUnprocessed, UnprocessedAdmin)



# dicom processed admin
class ProcessingStatusAdmin(ModelAdmin):
    list_display = (
        'patient_id',
        'patient_name',
        'patient_gender',
        'patient_modality',
        'patient_protocol',
        'patient_description',
        'status',
        'dicom_move_folder_status',
        'created_at',
    )
    readonly_fields =[
        'patient_id',
        'status',
        'dicom_move_folder_status',
        'yaml_attach_status',
        'created_at',
        'modified_at',
    ]
    list_filter = (
        'dicom_move_folder_status',
        'yaml_attach_status', 
        'patient_id__modality',
        'patient_id__studydate',
        'created_at'
    )
    search_fields = (
        'patient_id__patientid', 
        'patient_id__patientname',
        'patient_id__protocol',
        'patient_id__description',
    )
    list_select_related = ('patient_id',)
    list_per_page = 10
    search_help_text = "Search by patient ID, patient name, protocol, or description"

    @admin.display(description='Patient Name')
    def patient_name(self, obj):
        return obj.patient_id.patientname
    
    @admin.display(description='Gender')
    def patient_gender(self, obj):
        return obj.patient_id.gender

    @admin.display(description='Modality')
    def patient_modality(self, obj):
        return obj.patient_id.modality

    @admin.display(description='Protocol')
    def patient_protocol(self, obj):
        return obj.patient_id.protocol

    @admin.display(description='Description')
    def patient_description(self, obj):
        return obj.patient_id.description

admin.site.register(ProcessingStatus, ProcessingStatusAdmin)


class ModelYamlInfoAdmin(ModelAdmin):
    list_display = (
        'yaml_name', 
        'protocol', 
        'yaml_description',
        'created_at',
    )
    # readonly_fields = [
    #     'yaml_name',
    #     'yaml_path',
    #     'protocol',
    #     'file_hash',
    #     'yaml_description',
    #     'created_at',
    #     'modified_at',
    # ]
    search_fields = ('yaml_name','protocol','yaml_description')
    search_help_text = "Search by YAML name, protocol, or description"
    list_filter = ('yaml_name', 'protocol','created_at',)
    list_per_page = 10

admin.site.register(ModelYamlInfo, ModelYamlInfoAdmin)


# Upload dicom
# unzip_dir = "/home/sougata/draw-client-dir-test/uploaddicom"
@action(description='Send selected files to autosegmentation')
def send_to_autosegmentation(modeladmin, request, queryset):
    for obj in queryset:
        try:
            with zipfile.ZipFile(obj.dicom_file.path, 'r') as zip_ref:
                zip_ref.extractall(import_dir)
            
            obj.send_to_autosegmentation = True
            obj.save()

            messages.success(
                request, 
                f"Successfully {obj.dicom_file.name.split('/')[-1]} uploaded to autosegmentation"
            )

            dicom_series_separation(
                sourcedir = os.path.join(
                    import_dir,
                    os.path.splitext(os.path.basename(obj.dicom_file.path))[0]
                ),
                processeddir=processing_dir
            )
            
            for i in os.listdir(processing_dir):
                read_dicom_metadata(
                    dicom_series_path = os.path.join(processing_dir, i),
                    unprocess_dicom_path=os.path.join(unprocessed_dir, i),
                    deidentified_dicom_path=os.path.join(deidentified_dir, i)
                )

        except:
            print("Error unzipping file")
        

class uploadDicomAdmin(ModelAdmin):
    list_display = (
        'id', 
        'dicom_file',
        'send_to_autosegmentation',
        'created_at'
    )

    list_filter = ('send_to_autosegmentation','created_at',)
    exclude = ('send_to_autosegmentation',)
    search_fields = ('dicom_file',)
    actions = [send_to_autosegmentation]
    list_per_page = 10

admin.site.register(uploadDicom, uploadDicomAdmin)

class CopyDicomAdmin(ModelAdmin):
    list_display = (
        "sourcedirname",
        "dirsize",
        "copydate" 
    )
    list_per_page = 14
    search_fields = ('sourcedirname',)
    list_filter = ('copydate',)


admin.site.register(CopyDicom, CopyDicomAdmin)

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
class RuleInline(admin.TabularInline):
    model = Rule
    extra = 1
    
class RuleSetAdmin(ModelAdmin):
    inlines = [RuleInline]
    list_display = (
        "rule_set_name",
        "description",
        "model_yaml",
        "created_at",
        "modified_at",
    )
    list_per_page = 14
    search_fields = ('rule_set_name', "description", "model_yaml", "created_at")
    list_filter = ('rule_set_name', "model_yaml", "created_at")
   

admin.site.register(RuleSet, RuleSetAdmin)

# Tagname admin
class TagnameAdmin(ModelAdmin):
    pass

admin.site.register(TagName, TagnameAdmin)
