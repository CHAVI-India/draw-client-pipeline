from django.shortcuts import render, redirect
from django.utils import timezone
from .models import DicomSeriesProcessingModel
from django.db import connection

# Create your views here.

def dashboard(request):
    """
    Redirect to the main dashboard which now includes the series data
    """
    return redirect('/')
