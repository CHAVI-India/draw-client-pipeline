from django.shortcuts import render, redirect
from django.conf import settings
from requests.auth import HTTPBasicAuth
import requests
from django.contrib import messages
import pandas as pd
from django.http import JsonResponse  # Keep this import only once
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
import json  # Keep this import only once
from dicom_handler.dicomutils.create_yml import *
from django.urls import reverse
from dicom_handler.models import *
from dicom_handler.dicomutils.dicomseriesprocessing import *
from dicomapp.models import *
from django.views.decorators.csrf import csrf_protect
from collections import defaultdict
from api_client.models import *
from api_client.api_utils.proxy_config import get_session_with_proxy
from django.utils import timezone
import os
import re

logger = logging.getLogger(__name__)


# yaml saving path
templatefolderpath = os.path.normpath(os.path.join(settings.BASE_DIR, "yaml-templates"))
os.makedirs(templatefolderpath, exist_ok=True)
        
# Function to sanitize filenames
def sanitize_filename(filename):
    # Remove any path components and keep only alphanumeric, underscore, hyphen and period
    return re.sub(r'[^\w\-\.]', '_', os.path.basename(filename))

def index(request):
    # Get recent series data for the table
    recent_series = DicomSeriesProcessingModel.objects.all().order_by('-created_at')
    
    # Debug: Print count of series found
    logger.info(f"Number of series records found: {recent_series.count()}")
    
    context = {
        # Total Templates
        'total_templates': ModelYamlInfo.objects.count(),
        'total_rulesets': RuleSet.objects.count(),

        # Today's Segmented
        'todays_series_segmented': DicomSeriesProcessingModel.objects.filter(
            updated_at__date=timezone.now().date(),
            processing_status='RTSTRUCT_EXPORTED'
        ).count(),

        # Today's Unprocessed
        'todays_unprocessed_series': DicomSeriesProcessingModel.objects.filter(
            updated_at__date=timezone.now().date(),
            series_state='UNPROCESSED'
        ).count(),
        
        # series_with_error
        'series_with_error': DicomSeriesProcessingModel.objects.filter(
            processing_status='ERROR'
        ).count(),

        # total_series_segmented
        'total_series_segmented': DicomSeriesProcessingModel.objects.filter(
            processing_status='RTSTRUCT_EXPORTED'
        ).count(),
        
        # total_series_unprocessed
        'total_series_unprocessed': DicomSeriesProcessingModel.objects.filter(
            series_state='UNPROCESSED'
        ).count(),
        
        # Recent Series for the activity table
        'recent_series': recent_series,
        
        # # System Notifications
        # 'notifications': Notification.objects.order_by('-created_at')[:5],
    }
    
    # Debug: Print final context
    logger.info(f"Context prepared - recent_series count: {len(context['recent_series'])}")
    
    return render(request, 'dicom_handler/dashboard.html', context=context)

@login_required
def check_template(request):
    if request.method == 'POST':
        template_name = request.POST.get('templatename')
        description = request.POST.get('description')
        
        # Sanitize template name
        template_name = sanitize_filename(template_name)
        
        # Check if template name already exists
        template_name_yml = template_name + ".yml"
        template_exists = ModelYamlInfo.objects.filter(yaml_name=template_name_yml).exists()
        
        if template_exists:
            print(f"Template '{template_name}' already exists!")
            return render(request, 'dicom_handler/check_template.html', {
                'template_name': template_name,
                'description': description,
                'template_exists': True
            })
        
        # Only store in session and redirect if template doesn't exist
        request.session['template_name'] = template_name
        request.session['description'] = description
        return redirect('create-yml')
    
    # For GET requests, just render the empty form
    return render(request, 'dicom_handler/check_template.html')


@login_required
def create_yml(request):
    try:
        # Create a session with proxy settings
        session = get_session_with_proxy()
        
        # Fetch API data using the session
        api_url = settings.API_URL
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        raw_data = response.json()

        if request.method == 'POST':
            template_name = request.POST.get('templateName')
            description = request.POST.get('description')
            selected_model_ids = request.POST.getlist('selected_model_ids')
            selected_map_ids = request.POST.getlist('selected_map_ids')

            # Sanitize template name to prevent path traversal
            template_name = sanitize_filename(template_name)

            if not selected_model_ids:
                messages.error(request, 'Please select at least one model')
                return render(request, 'dicom_handler/create_yml.html', {
                    'apidata': raw_data,
                    'template_name': template_name,
                    'description': description
                })

            # Create list of selected model data
            selected_data = []
            for model_id, map_id in zip(selected_model_ids, selected_map_ids):
                for info in raw_data:
                    if str(info['model_id']) == str(model_id):
                        for map_info in info['modelmap']:
                            if str(map_info['mapid']) == str(map_id):
                                selected_data.append({
                                    'model_id': info['model_id'],
                                    'model_name': info['model_name'],
                                    'mapid': map_info['mapid'],
                                    'map_tg263_primary_name': map_info['map_tg263_primary_name'],
                                    'model_config': info.get('model_config', ''),
                                    'model_trainer_name': info.get('model_trainer_name', ''),
                                    'model_postprocess': info.get('model_postprocess', '')
                                })

            # Create DataFrame
            df = pd.DataFrame(selected_data)
            
            # Prepare YAML file with safe name
            yaml_name = sanitize_filename(f"{template_name}.yml")
            
            # Create YAML file using the safe function from create_yml.py
            create_yaml_from_pandas_df(df, templatefolderpath, yaml_name)
            
            # Get normalized path for storage
            safe_yaml_path = os.path.normpath(os.path.join(templatefolderpath, yaml_name))

            # Ensure the path is within the allowed directory
            if not safe_yaml_path.startswith(templatefolderpath):
                raise ValueError("Invalid YAML path: potential path traversal attempt")

            created_file_hash = calculate_hash(safe_yaml_path)

            # Save to database
            ModelYamlInfo.objects.create(
                yaml_name=yaml_name,
                yaml_path=safe_yaml_path,
                protocol=yaml_name,
                file_hash=created_file_hash,
                yaml_description=description
            )

            messages.success(request, 'Template created successfully!')
            print("Redirecting to autosegmentation-template page...")
            return redirect('autosegmentation-template')
        
        # For GET request
        return render(request, 'dicom_handler/create_yml.html', {
            'apidata': raw_data,
            'model_details_api': os.getenv('MODEL_API_URL'),
            'template_name': request.session.get('template_name'),
            'description': request.session.get('description')
        })

    except requests.RequestException as e:
        messages.error(request, f'Failed to fetch API data: {str(e)}')
        return render(request, 'dicom_handler/create_yml.html', {
            'template_name': request.session.get('template_name'),
            'description': request.session.get('description')
        })
    except Exception as e:
        # Add more detailed error logging
        print("Error in create_yml:", str(e))
        messages.error(request, f'An error occurred: {str(e)}')
        return render(request, 'dicom_handler/create_yml.html', {
            'apidata': raw_data if 'raw_data' in locals() else None,
            'template_name': request.session.get('template_name'),
            'description': request.session.get('description')
        })



@require_http_methods(["GET"])
def autosegmentation_template(request):
    try:
        # Get the latest created template from database
        latest_template = ModelYamlInfo.objects.latest('id')
        
        # Read and parse the YAML file
        yaml_path = latest_template.yaml_path
        if not yaml_path:
            raise ValueError("YAML path is not set in the database")
        
        # Normalize and validate the path is within templatefolderpath
        normalized_yaml_path = os.path.normpath(os.path.abspath(yaml_path))
        normalized_template_path = os.path.normpath(os.path.abspath(templatefolderpath))
        
        if not normalized_yaml_path.startswith(normalized_template_path):
            raise ValueError("Invalid YAML path: potential path traversal attempt")
            
        with open(normalized_yaml_path, 'r') as file:
            yaml_data = yaml.safe_load(file)

        # Extract models data
        models_data = yaml_data.get('models', {})
        
        # Convert to list format for template
        grouped_models = []
        for model_id, model_info in models_data.items():
            model_info['model_id'] = model_id
            grouped_models.append(model_info)

        context = {
            'template_name': latest_template.yaml_name.replace('.yml', ''),
            'description': latest_template.yaml_description,
            'grouped_models': grouped_models,
        }

        return render(request, 'dicom_handler/yaml_view.html', context)

    except ModelYamlInfo.DoesNotExist:
        messages.error(request, 'No templates found.')
        return redirect('create-yml')
    
    except ValueError as e:
        print(f"Error in yaml view: {str(e)}")
        messages.error(request, str(e))
        return redirect('create-yml')
    
    except Exception as e:
        print(f"Error in yaml view: {str(e)}")
        messages.error(request, f'Error loading template: {str(e)}')
        return redirect('create-yml')


