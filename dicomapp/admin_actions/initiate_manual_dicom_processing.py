from django.contrib import messages
from dicomapp.tasks import send_dicom_to_remote_server_pipeline

def initiate_manual_dicom_processing(modeladmin, request, queryset):
    '''
    This function will be used as an admin action to the CopyDicomTaskModel.
    The user will select the CopyDicomTaskModel instances to be processed.
    After clicking the action the function will initiate the celery task chain send_dicom_to_remote_server_pipeline. 
    The datastore path will be the source directory of the CopyDicomTaskModel instance.
    '''
    try:
        for copy_dicom in queryset:
            # Start the DICOM processing pipeline for each selected instance
            result = send_dicom_to_remote_server_pipeline.delay(copy_dicom.source_directory)
            
            # Log success message
            messages.success(
                request,
                f'Started DICOM processing pipeline for {copy_dicom.source_directory} with chain ID: {result.id}'
            )
    except Exception as e:
        # Log error message if something goes wrong
        messages.error(
            request,
            f'Error initiating DICOM processing: {str(e)}'
        )
