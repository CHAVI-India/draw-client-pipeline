

from django.contrib import admin
from django.urls import path
from dicom_handler.views import *

urlpatterns = [
    path("", index, name = "index"),
    path('check-template/', check_template, name='check-template'),
    path('create-yml/', create_yml, name='create-yml'),
    path('autosegmentation-template/', autosegmentation_template, name='autosegmentation-template'),
]
