from django.contrib import admin
from django.urls import path
from dicom_handler.views import *
from django.views.generic import TemplateView

urlpatterns = [
    path("", index, name = "index"),
    path('check-template/', check_template, name='check-template'),
    path('create-yml/', create_yml, name='create-yml'),
    path('autosegmentation-template/', autosegmentation_template, name='autosegmentation-template'),
    path('privacy-policy/', TemplateView.as_view(template_name='policies/privacy_policy.html'), name='privacy-policy'),
    path('terms-of-service/', TemplateView.as_view(template_name='policies/terms_of_service.html'), name='terms-of-service'),
    path('contact/', TemplateView.as_view(template_name='policies/contact.html'), name='contact'),
]
