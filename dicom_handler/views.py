

from django.shortcuts import render, redirect
from django.conf import settings
from requests.auth import HTTPBasicAuth
import requests
from django.contrib import messages
import pandas as pd
from django.http import JsonResponse  # Keep this import only once
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
import json  # Keep this import only once
from dicom_handler.dicomutils.create_yml import *
from django.urls import reverse
from dicom_handler.models import *
from .dicomutils.dicomseriesprocessing import *

# yaml saving path
# try:
#     templatefolderpath = DicomPathConfig.objects.values("templatefolderpath").first()["templatefolderpath"]
# except:
templatefolderpath = os.path.join(os.getcwd(), "yaml-templates")
os.makedirs(templatefolderpath, exist_ok=True)
    


def index(request):
    return render(request, 'index.html')


@require_http_methods(["GET", "POST"])
def create_yml(request):
    api_url = settings.API_URL
   
    try:
        response = requests.get(
            api_url,
            # auth=HTTPBasicAuth(username, password),
            timeout=10
        )
        
        response.raise_for_status()
        raw_data = response.json()
        raw_data["model_api_endpoint"] = "os.getenv"
        # print(raw_data)

    except:
        messages.error(request, "API Error: Unable to fetch data from the API.")

    if request.method == 'POST':
        data = json.loads(request.body)
    
        template_name = data.get('templateName')
        description = data.get('description')
        selected_models = data.get('selectedModels', [])

        try:
            data = pd.DataFrame(selected_models)
            data["model_id"] = data['model_id'].astype(int)

            # yaml save path
            yaml_name = f"{template_name}.yml"
            yaml_path = os.path.join(
                templatefolderpath, yaml_name 
            )
            print(yaml_path)
            create_yaml_from_pandas_df(data, templatefolderpath, yaml_name)
            created_file_hash = calculate_hash(yaml_path)
            print("hash value: ",created_file_hash)

            ModelYamlInfo.objects.create(
                yaml_name=yaml_name,
                yaml_path = yaml_path,
                protocol = yaml_name,
                file_hash = created_file_hash,
                yaml_description=description
            )

            # Store data in session for the next page
            request.session['template_name'] = template_name
            request.session['description'] = description
            request.session['selected_models'] = selected_models
            request.session['api_data'] = raw_data

            # Return JSON response with success status and redirect URL
            return JsonResponse({
                'status': 'success',
                'message': 'YAML file created successfully!',
                'redirect_url': reverse('autosegmentation_template')
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
        
    return render(request, 'create_yml.html', context={
        'apidata': raw_data, 
        'api_url': os.getenv("MODEL_API_URL")
        }
    )


from collections import defaultdict

@require_http_methods(["GET"])
def autosegmentation_template(request):
    # Retrieve data from session
    context = {
        'template_name': request.session.get('template_name'),
        'description': request.session.get('description'),
        'selected_models': request.session.get('selected_models'),
        'apidata': request.session.get('api_data')
    }
    # print("context")
    # print(context["selected_models"])

    # Group models by model_id
    models_by_id = defaultdict(list)
    for model in context["selected_models"]:
        models_by_id[model['model_id']].append(model)
    
    # Prepare grouped models with map as a dictionary
    grouped_models = []
    for model_id, models in models_by_id.items():
        # Prepare the basic model info
        model_info = {
            'model_id': model_id,
            'name': models[0]['model_name'],  # Assuming all models with the same model_id have the same name
            'config': models[0]['model_config'],  # Same for config
            'trainer_name': models[0]['model_trainer_name'],  # Same for trainer name
            'postprocess': models[0]['model_postprocess'],  # Same for postprocess
            'map': {}  # Initialize the map dictionary
        }
        
        # Add mapid and map_tg263_primary_name to the map dictionary
        for model in models:
            model_info['map'][model['mapid']] = model['map_tg263_primary_name']
        
        grouped_models.append(model_info)

    return render(request, 'yamlview.html', {
        'template_name': request.session.get('template_name'),
        'description': request.session.get('description'),
        'grouped_models': grouped_models,
    })



def yaml_viewer(request):
    return render(request, 'yaml_view.html')

def list_yaml_files(request):
    try:
        # Specify your YAML files directory relative to your project
        yaml_dir = os.path.join("/home/sougata/sougata/DRAW-Pipeline-Prediction/config_yaml")
        yaml_files = [f for f in os.listdir(yaml_dir) if f.endswith('.yml')]
        return JsonResponse(yaml_files, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_yaml_content(request, filename):
    try:
        yaml_dir =os.path.join("/home/sougata/sougata/DRAW-Pipeline-Prediction/config_yaml")
        file_path = os.path.join(yaml_dir, filename)
        
        # Check if file path is safe (within yaml_dir)
        if not file_path.startswith(yaml_dir):
            raise Exception("Invalid file path")
            
        with open(file_path, 'r') as file:
            yaml_content = file.read()
            # Parse and dump YAML to ensure proper formatting
            yaml_data = yaml.safe_load(yaml_content)
            formatted_yaml = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False)
            return JsonResponse({'content': formatted_yaml})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)