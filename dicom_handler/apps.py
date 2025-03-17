from django.apps import AppConfig
from django.core.management import call_command


class DicomHandlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dicom_handler'

    # def ready(self):
    #     # Call the custom command to start APScheduler when the app is ready
    #     call_command('runapscheduler')
