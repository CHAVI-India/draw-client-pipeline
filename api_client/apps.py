from django.apps import AppConfig
import sys

class ApiClientConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api_client'
    
    # def ready(self):
    #     """Initialize scheduler when Django starts."""
    #     # Don't start scheduler when running migrations
    #     if 'migrate' not in sys.argv:
    #         from . import scheduler
    #         scheduler.start_scheduler()
