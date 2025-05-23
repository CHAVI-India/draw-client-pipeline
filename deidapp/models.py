from django.db import models

# Create your models here.

class Patient(models.Model):
    patient_id = models.CharField(max_length=100,primary_key=True)
    deidentified_patient_id = models.CharField(max_length=100,null=True,blank=True)
    patient_name = models.CharField(max_length=100,null=True,blank=True)
    patient_birth_date = models.DateField(null=True,blank=True)
    deidentified_patient_birth_date = models.DateField(null=True,blank=True)
    deidentified_patient_name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=[ 'deidentified_patient_id','patient_name','deidentified_patient_birth_date','deidentified_patient_name'])
        ]

class DicomStudy(models.Model):
    study_instance_uid = models.CharField(max_length=100,primary_key=True)
    patient = models.ForeignKey(Patient,on_delete=models.CASCADE)
    deidentified_study_instance_uid = models.CharField(max_length=100,null=True,blank=True)
    study_date = models.DateField(null=True,blank=True)
    deidentified_study_date = models.DateField(null=True,blank=True)
    study_description = models.CharField(max_length=100,null=True,blank=True)
    study_id = models.CharField(max_length=100,null=True,blank=True)
    deidentified_study_id = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=[ 'deidentified_study_instance_uid','study_date','deidentified_study_date'])
        ]

class DicomSeries(models.Model):
    series_instance_uid = models.CharField(max_length=100,primary_key=True)
    study = models.ForeignKey(DicomStudy,on_delete=models.CASCADE)
    task_id = models.CharField(max_length=100,null=True,blank=True)
    dicom_series_processing_id = models.CharField(max_length=100,null=True,blank=True)
    deidentified_series_instance_uid = models.CharField(max_length=100,null=True,blank=True)
    series_date = models.DateField(null=True,blank=True)
    deidentified_series_date = models.DateField(null=True,blank=True)
    frame_of_reference_uid = models.CharField(max_length=100,null=True,blank=True)
    deidentified_frame_of_reference_uid = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=[ 'deidentified_series_instance_uid','series_date','deidentified_series_date','frame_of_reference_uid','deidentified_frame_of_reference_uid'])
        ]

class DicomInstance(models.Model):
    sop_instance_uid = models.CharField(max_length=100,primary_key=True)
    deidentified_sop_instance_uid = models.CharField(max_length=100,null=True,blank=True)
    series = models.ForeignKey(DicomSeries,on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=[ 'deidentified_sop_instance_uid'])
        ]

class RTStructFile(models.Model):
    series_instance_uid = models.CharField(max_length=100, primary_key=True)
    dicom_series = models.ForeignKey(DicomSeries,on_delete=models.CASCADE,null=True,blank=True)    
    original_file_path = models.CharField(max_length=100,null=True,blank=True)
    processed_file_path = models.CharField(max_length=100,null=True,blank=True)
    processing_date = models.DateField(null=True,blank=True)
    processing_status = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)