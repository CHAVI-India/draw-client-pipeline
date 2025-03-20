

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
from django.views.decorators.csrf import csrf_protect


# yaml saving path
try:
    templatefolderpath = DicomPathConfig.objects.values("templatefolderpath").first()["templatefolderpath"]
except:
    templatefolderpath = os.path.join(os.getcwd(), "yaml-templates")
    os.makedirs(templatefolderpath, exist_ok=True)
        

def index(request):
    return render(request, 'index.html')

def check_template(request):
    if request.method == 'POST':
        template_name = request.POST.get('templatename')
        description = request.POST.get('description')
        
        # Print to console for debugging
        # print("Template Name:", template_name)
        # print("Description:", description)
        
        # Check if template name already exists
        template_name_yml = template_name + ".yml"
        template_exists = ModelYamlInfo.objects.filter(yaml_name=template_name_yml).exists()
        
        if template_exists:
            print(f"Template '{template_name}' already exists!")
            return render(request, 'check_template.html', {
                'template_name': template_name,
                'description': description,
                'template_exists': True
            })
        
        # Only store in session and redirect if template doesn't exist
        request.session['template_name'] = template_name
        request.session['description'] = description
        return redirect('create-yml')
    
    # For GET requests, just render the empty form
    return render(request, 'check_template.html')


def create_yml(request):
    try:
        # Fetch API data
        api_url = settings.API_URL
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        raw_data = response.json()

        if request.method == 'POST':
            template_name = request.POST.get('templateName')
            description = request.POST.get('description')
            selected_model_ids = request.POST.getlist('selected_model_ids')  # Changed from selected_models
            selected_map_ids = request.POST.getlist('selected_map_ids')  # Added to get map IDs
            # print("Selected Model IDs:", selected_model_ids)
            # print("Selected Map IDs:", selected_map_ids)
            if not selected_model_ids:
                messages.error(request, 'Please select at least one model')
                return render(request, 'create_yml.html', {
                    'apidata': raw_data,
                    'template_name': template_name,
                    'description': description
                })

            # Create list of selected model data
            selected_data = []
            for model_id, map_id in zip(selected_model_ids, selected_map_ids):
                for info in raw_data:
                    if str(info['model_id']) == str(model_id):  # Changed from modelId to model_id
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

            # Print for debugging
            print("Selected Data --- :", selected_data)

            # Create DataFrame
            df = pd.DataFrame(selected_data)
            
            # Prepare YAML file
            yaml_name = f"{template_name}.yml"
            yaml_path = os.path.join(templatefolderpath, yaml_name)

            # Create YAML file
            create_yaml_from_pandas_df(df, templatefolderpath, yaml_name)
            created_file_hash = calculate_hash(yaml_path)

            # Save to database
            ModelYamlInfo.objects.create(
                yaml_name=yaml_name,
                yaml_path=yaml_path,
                protocol=yaml_name,
                file_hash=created_file_hash,
                yaml_description=description
            )

            messages.success(request, 'Template created successfully!')
            print("Redirecting to autosegmentation-template page...")
            return redirect('autosegmentation-template')
        
        # For GET request
        return render(request, 'create_yml.html', {
            'apidata': raw_data,
            'template_name': request.session.get('template_name'),
            'description': request.session.get('description')
        })

    except requests.RequestException as e:
        messages.error(request, f'Failed to fetch API data: {str(e)}')
        return render(request, 'create_yml.html', {
            'template_name': request.session.get('template_name'),
            'description': request.session.get('description')
        })
    except Exception as e:
        # Add more detailed error logging
        print("Error in create_yml:", str(e))
        messages.error(request, f'An error occurred: {str(e)}')
        return render(request, 'create_yml.html', {
            'apidata': raw_data,
            'template_name': request.session.get('template_name'),
            'description': request.session.get('description')
        })



# def create_yml(request):
#     api_url = settings.API_URL
    
#     try:
#         response = requests.get(
#             api_url,
#             # auth=HTTPBasicAuth(username, password),
#             timeout=10
#         )
        
#         response.raise_for_status()
#         raw_data = response.json()

#     except:
#         messages.error(request, "API Error: Unable to fetch data from the API.")

#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
        
#             template_name = data.get('templateName')
#             description = data.get('description')
#             selected_models = data.get('selectedModels', [])

#             # Print received data for debugging
#             print("Received Data:")
#             print("Template Name:", template_name)
#             print("Description:", description)
#             print("Selected Models:", selected_models)

#             # Prepare data for DataFrame
#             processed_data = []
#             for model in selected_models:
#                 processed_data.append({
#                     'model_id': model['modelId'],
#                     'model_name': model['modelName'],
#                     'mapid': model['mapId'],
#                     'structure_name': model['structureName'],
#                     'model_config': model.get('config', ''),
#                     'model_trainer_name': model.get('trainerName', ''),
#                     'model_postprocess': model.get('postprocess', '')
#                 })

#             # Create DataFrame
#             df = pd.DataFrame(processed_data)
#             df["model_id"] = df['model_id'].astype(int)

#             # yaml save path
#             yaml_name = f"{template_name}.yml"
#             yaml_path = os.path.join(templatefolderpath, yaml_name)
            
#             print("Creating YAML at:", yaml_path)
            
#             # Create YAML file
#             create_yaml_from_pandas_df(df, templatefolderpath, yaml_name)
#             created_file_hash = calculate_hash(yaml_path)

#             # Save to database
#             ModelYamlInfo.objects.create(
#                 yaml_name=yaml_name,
#                 yaml_path=yaml_path,
#                 protocol=yaml_name,
#                 file_hash=created_file_hash,
#                 yaml_description=description
#             )

#             # Store data in session for the next page
#             request.session['template_name'] = template_name
#             request.session['description'] = description
#             request.session['selected_models'] = processed_data

#             return JsonResponse({
#                 'status': 'success',
#                 'message': 'YAML file created successfully!',
#                 'redirect_url': reverse('autosegmentation-template')
#             })
            
#         except Exception as e:
#             print("Error creating template:", str(e))
#             return JsonResponse({
#                 'status': 'error',
#                 'message': str(e)
#             }, status=400)
        

#     return render(request, 'create_yml.html', {
#                 'apidata': raw_data,
#                 'template_name': request.session.get('template_name'),
#                 'description': request.session.get('description')
#             })


from collections import defaultdict


@require_http_methods(["GET"])
def autosegmentation_template(request):
    try:
        # Get the latest created template from database
        latest_template = ModelYamlInfo.objects.latest('id')
        
        # Read and parse the YAML file
        yaml_path = latest_template.yaml_path
        with open(yaml_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
        
        print("Loaded YAML data:", yaml_data)

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

        return render(request, 'yamlview.html', context)

    except ModelYamlInfo.DoesNotExist:
        messages.error(request, 'No templates found.')
        return redirect('create-yml')
    except Exception as e:
        print(f"Error in yaml view: {str(e)}")
        messages.error(request, f'Error loading template: {str(e)}')
        return redirect('create-yml')





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
