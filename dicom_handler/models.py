from django.db import models
import os
from django.core.exceptions import ValidationError
from urllib.parse import urlparse



class DicomPathConfig(models.Model):
    id = models.AutoField(primary_key=True)
    datastorepath = models.TextField(null=True, help_text="Enter the full path to the datastore which is the remote folder from the DICOM data will be imported. This can be a remote folder in which case the full path is required. We would suggest that in such a situation the remote folder is mapped as a shared drive on the machine where this client runs.")

    class Meta:
        db_table = "dicom_path_config"
        verbose_name = "Dicom Path Configuration"

    def save(self, *args, **kwargs):
        if DicomPathConfig.objects.exists() and not self.pk:
            # If you're trying to create a second instance, don't save
            raise ValidationError("There can only be one DicomPathConfig instance")
        return super().save(*args, **kwargs)
        
    @classmethod
    def get_instance(cls):
        instance, created = cls.objects.get_or_create(pk=1)
        return instance


# import config
class DicomImportConfig(models.Model):
    id = models.AutoField(primary_key=True)
    pullinterval = models.PositiveIntegerField()

class ProcessingStatusChoices(models.TextChoices):
    COPIED = 'COPIED', 'COPIED'
    PROCESSED = 'PROCESSED', 'PROCESSED'
    FAILED = 'FAILED', 'FAILED'

# Dicom copy
class CopyDicom(models.Model):
    id = models.AutoField(primary_key=True)
    sourcedirname = models.TextField()
    destinationdirname = models.TextField()
    dircreateddate = models.DateTimeField(null=True)
    dirmodifieddate = models.DateTimeField(null=True)
    dirsize = models.PositiveIntegerField()
    processing_status = models.CharField(max_length=255, choices=ProcessingStatusChoices.choices, null=True)
    copydate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sourcedirname
    
    class Meta:
        db_table = 'copy_dicom'
        verbose_name = 'Copied DICOM Data'
        verbose_name_plural = 'Copied DICOM Data'


class DicomSeriesProcessing(models.Model):
    id = models.AutoField(primary_key=True)
    patientid = models.CharField(max_length=10)
    patientname = models.CharField(max_length=255)
    gender = models.CharField(max_length=10)
    studyid = models.CharField(max_length=255)
    seriesid = models.CharField(max_length=255)
    seriesfilepath = models.TextField()
    studydate = models.DateField()
    modality = models.CharField(max_length=10)
    protocol = models.CharField(max_length=255, null=True)
    description = models.CharField(max_length=255)
    dicomcount = models.PositiveSmallIntegerField(null=True)
    series_split_done = models.BooleanField(default=False)
    processing_start = models.DateTimeField(null=True)
    processing_end = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.studyid
    
    class Meta:
        db_table = "dicom_import"
        verbose_name = "Dicom Series for Processing"
        verbose_name_plural = "Dicom Series for Processing"


class ModelYamlInfo(models.Model):
    id = models.AutoField(primary_key=True)
    yaml_name = models.CharField(max_length=255, unique=True)
    yaml_path = models.TextField()
    protocol = models.CharField(max_length=255)
    file_hash = models.CharField(max_length=128, null=True)
    yaml_description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f"{self.yaml_name} | {self.protocol}" 
    
    class Meta:
        managed = True
        db_table = "model_yaml_info"
        verbose_name = "Autosegmentation Template"


class DicomUnprocessed(models.Model):
    id = models.AutoField(primary_key=True)
    patientid = models.CharField(max_length=10)
    patientname = models.CharField(max_length=255)
    gender = models.CharField(max_length=10)
    series_folder_location = models.TextField(null=True)
    studyid = models.CharField(max_length=255)
    seriesid = models.CharField(max_length=255)
    studydate = models.DateField()
    modality = models.CharField(max_length=10)
    protocol = models.CharField(max_length=255, null=True)
    description = models.CharField(max_length=255)
    dicomcount = models.PositiveSmallIntegerField(null=True)
    yaml_attached = models.ForeignKey(ModelYamlInfo, on_delete=models.CASCADE, null=True, blank=True)
    unprocessed = models.BooleanField(default=False, null=True)
    ready_for_deidentification = models.BooleanField(default=False, null=True)
    # processingstatus = models.ForeignKey(ProcessingStatus, on_delete=models.CASCADE, db_column='status', null=True)
    processing_start = models.DateTimeField(null=True)
    processing_end = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.patientid
    
    class Meta:
        db_table = "dicom_unprocessed"
        verbose_name = "Unprocessed DICOM Data"
        verbose_name_plural = "Unprocessed DICOM Data"

class ProcessingStatus(models.Model):
    id = models.AutoField(primary_key=True)
    patient_id = models.ForeignKey(DicomUnprocessed, on_delete=models.CASCADE, null=True)
    status = models.CharField(max_length=255, null=True)
    dicom_move_folder_status = models.CharField(max_length=255)
    yaml_attach_status = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
  

    # def __str__(self):
    #     return self.status
    
    class Meta:
        db_table = 'processed_status'
        verbose_name = 'DICOM Processing Status'
        verbose_name_plural = 'DICOM Processing Status'


class SeriesMetaData(models.Model):
    series = models.ForeignKey(
        DicomSeriesProcessing, 
        on_delete=models.CASCADE,
        db_column="seriesid"
    )
    
    tag = models.CharField(max_length=255)
    tagname = models.CharField(max_length=255)
    tagvalue = models.TextField()


    def __str__(self):
        return self.tagname
    
    class Meta:
        db_table = "series_metadata"
        verbose_name = "Series Metadata"


class RuleSet(models.Model):
    id = models.AutoField(primary_key=True)
    rule_set_name = models.CharField(max_length=255, unique=True,help_text="Enter a name for the rule set. This must be a unique name and not match any other existing rule set.")
    description = models.CharField(max_length=255, help_text="Enter a description for the rule set.")
    model_yaml = models.OneToOneField(ModelYamlInfo, on_delete=models.CASCADE, null=True, help_text="Select the model yaml file for the rule set.")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self): 
        return self.rule_set_name
    
    class Meta:
        db_table = "rule_set"
        verbose_name = "Rule Set For Matching Template"
        verbose_name_plural = "Rule Sets For Matching Template"
    
class TagName(models.Model):
    id = models.AutoField(primary_key=True)
    tag_name = models.CharField(max_length=255, help_text="Enter the DICOM tag name. Please ensure that it matches the DICOM tag name properly")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self):
        return self.tag_name
    
    class Meta:
        db_table = "tag_name"
        verbose_name = "DICOM Tag List"
        verbose_name_plural = "DICOM Tag List"

class Rule(models.Model):
    id = models.AutoField(primary_key=True)
    rule_set = models.ForeignKey(RuleSet, on_delete=models.PROTECT)
    tag_name = models.ForeignKey(TagName, on_delete=models.PROTECT)
    tag_value = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)

    # def __str__(self):
    #     return self.id
    
    class Meta:
        db_table = "rule"
        verbose_name = "Rule"


class uploadDicom(models.Model):
    id = models.AutoField(primary_key=True)
    dicom_file = models.FileField(upload_to='folder_for_dicom_upload/')
    send_to_autosegmentation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)


    def __str__(self):
        return self.dicom_file.name
    

    class Meta:
        db_table = "upload_images"
        verbose_name = "Upload Images"
        verbose_name_plural = "Upload Images"