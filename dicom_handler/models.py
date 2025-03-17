from django.db import models
import os
from django.core.exceptions import ValidationError
from urllib.parse import urlparse
from solo.models import SingletonModel



class DicomPathConfig(SingletonModel):
    id = models.AutoField(primary_key=True)
    datastorepath = models.TextField(null=True)
    dicomimportfolderpath = models.TextField(null=True)
    dicomprocessingfolderpath = models.TextField(null=True)
    dicomnonprocessedfolderpath = models.TextField(null=True)
    deidentificationfolderpath = models.TextField(null=True)
    finalrtstructfolderpath = models.TextField(null=True)
    templatefolderpath = models.TextField(null=True)

    class Meta:
        db_table = "dicom_path_config"
        verbose_name = "Dicom Path Configaration"


# import config
class DicomImportConfig(models.Model):
    id = models.AutoField(primary_key=True)
    pullinterval = models.PositiveIntegerField()


# Dicom copy
class CopyDicom(models.Model):
    id = models.AutoField(primary_key=True)
    sourcedirname = models.TextField()
    destinationdirname = models.TextField()
    dircreateddate = models.DateTimeField(null=True)
    dirmodifieddate = models.DateTimeField(null=True)
    dirsize = models.PositiveIntegerField()
    copydate = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.sourcedirname
    
    class Meta:
        db_table = 'copy_dicom'
        verbose_name = 'Copy Dicom'


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
    sop_instance_uid = models.CharField(max_length=255, unique=True, null=True)
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
        verbose_name = "Dicom Import"


class ModelYamlInfo(models.Model):
    id = models.AutoField(primary_key=True)
    yaml_name = models.CharField(max_length=255)
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
    rule_set_name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=255)
    model_yaml = models.OneToOneField(ModelYamlInfo, on_delete=models.CASCADE, null=True)
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
    tag_name = models.CharField(max_length=255)
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
    dicom_file = models.FileField(upload_to='uploaddicom/')
    send_to_autosegmentation = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    modified_at = models.DateTimeField(auto_now=True, null=True)


    def __str__(self):
        return self.dicom_file.name
    

    class Meta:
        db_table = "upload_images"
        verbose_name = "Upload Images"
        verbose_name_plural = "Upload Images"