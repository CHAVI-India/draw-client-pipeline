

from django.contrib import admin
from django.urls import path
from dicom_handler.views import *

urlpatterns = [
    path("", index, name = "index"),
    path('create-yml/', create_yml, name='create-yml'),
    path('autosegmentation-template/', autosegmentation_template, name='autosegmentation-template'),
    path('list-yaml-files/', list_yaml_files, name='list_yaml_files'),
    path('yaml-content/<str:filename>/', get_yaml_content, name='get_yaml_content'),
    path('check-template/', check_template, name='check-template'),
]
