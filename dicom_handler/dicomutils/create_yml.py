
import pandas as pd
import yaml
import os
import numpy as np
import logging


# # Get loggers for different purposes
logger = logging.getLogger('django_log_lens.client')
# logger = logging.getLogger('django')


# def create_yaml_from_pandas_df(data, save_yaml_path, yaml_name):
#     try:
#         # Log start of function
#         logger.debug(f"Starting YAML creation for {yaml_name}")
        
#         # Convert dictionary to DataFrame if a dictionary is passed
#         if isinstance(data, dict):
#             df = pd.DataFrame(data)
#             logger.debug("Converted dictionary to DataFrame")
#         else:
#             df = data
#             logger.debug("Using provided DataFrame")
#             print(df)

#         # Group the data by model_name
#         try:
#             grouped = df.groupby('model_id').agg({
#                 'model_name': lambda x: str(x.iloc[0]).replace("'", "").strip(),
#                 'model_config': lambda x: str(x.iloc[0]).replace("'", "").strip(),
#                 'mapid': lambda x: str(x.iloc[0]).replace("'", "").strip(),
#                 'map_tg263_primary_name': lambda x: {str(df.iloc[x.index]['mapid'].iloc[0]): str(x.iloc[0])},  # Modified this line
#                 'model_trainer_name': lambda x: str(x.iloc[0]),
#                 'model_postprocess': lambda x: str(x.iloc[0])
#             }).to_dict('index')
#             logger.info("Successfully grouped data by model_id")
        
#         except Exception as e:
#             logger.error(f"Error during data grouping: {str(e)}")
#             print(f"Error during data grouping: {str(e)}")
#             raise

#         print(grouped)

#         # Create the final structure
#         try:
#             yaml_dict = {
#                 'name': data["model_name"].iloc[0],
#                 'protocol': data["model_name"].iloc[0],
#                 'models': {
#                     model_name: {
#                         'name': data["model_name"],
#                         'config': data['model_config'],
#                         'map': data['map_tg263_primary_name'],
#                         'trainer_name': data['model_trainer_name'],
#                         'postprocess': data["model_postprocess"]
#                     }
#                     for model_name, data in grouped.items()
#                 }
#             }
#             print(yaml_dict)
#             logger.info("Successfully created YAML dictionary structure")
#         except Exception as e:
#             logger.error(f"Error creating YAML dictionary: {str(e)}")
#             raise

#         # Save to file if path is provided
#         save_yaml_path = os.path.join(save_yaml_path, yaml_name)
#         if save_yaml_path is not None:
#             try:
#                 with open(save_yaml_path, 'w') as f:
#                     yaml.dump(yaml_dict, f, sort_keys=False, default_flow_style=False)
#                 logger.info(f"Successfully saved YAML file to {save_yaml_path}")
#             except Exception as e:
#                 logger.error(f"Error saving YAML file: {str(e)}")
#                 raise

#         return "yaml_dict"

#     except Exception as e:
#         logger.error(f"Unexpected error in create_yaml_from_pandas_df: {str(e)}")
#         raise



def create_yaml_from_pandas_df(data, save_yaml_path, yaml_name):
    try:
        # Log start of function
        logger.debug(f"Starting YAML creation for {yaml_name}")
        
        # Convert dictionary to DataFrame if a dictionary is passed
        if isinstance(data, dict):
            df = pd.DataFrame(data)
            logger.debug("Converted dictionary to DataFrame")
        else:
            df = data
            logger.debug("Using provided DataFrame")
            print("Input DataFrame:")
            print(df)

        # Group the data by model_name
        try:
            # First create base aggregation for non-map fields
            grouped = df.groupby('model_id').agg({
                'model_name': 'first',
                'model_config': 'first',
                'model_trainer_name': 'first',
                'model_postprocess': lambda x: None if x.iloc[0] == 'null' else x.iloc[0]
            }).to_dict('index')

            # Then add the complete map for each model_id
            for model_id in grouped.keys():
                model_df = df[df['model_id'] == model_id]
                map_dict = dict(zip(
                    model_df['mapid'].astype(int), 
                    model_df['map_tg263_primary_name']
                ))
                # grouped[model_id]['map'] = map_dict
                # Convert to OrderedDict to maintain order
                grouped[model_id]['map'] = dict(sorted(map_dict.items()))

            logger.info("Successfully grouped data by model_id")
            print("Grouped data:")
            print(grouped)

        except Exception as e:
            logger.error(f"Error during data grouping: {str(e)}")
            print(f"Error during data grouping: {str(e)}")
            raise

        # Create the final structure
        try:
            yaml_dict = {
                'name': yaml_name.replace('.yml', ''),
                'protocol': yaml_name.replace('.yml', ''),
                'models': {
                    int(model_id): {
                        'name': model_data['model_name'],
                        'config': model_data['model_config'],
                        'map': model_data['map'],
                        'trainer_name': model_data['model_trainer_name'],
                        'postprocess': model_data['model_postprocess']
                    }
                    for model_id, model_data in grouped.items()
                }
            }
            print("YAML dictionary:")
            print(yaml_dict)
            logger.info("Successfully created YAML dictionary structure")
        except Exception as e:
            logger.error(f"Error creating YAML dictionary: {str(e)}")
            raise

        # Save to file if path is provided
        save_yaml_path = os.path.join(save_yaml_path, yaml_name)
        if save_yaml_path is not None:
            try:
                with open(save_yaml_path, 'w') as f:
                    yaml.dump(yaml_dict, f, sort_keys=False, default_flow_style=False)
                logger.info(f"Successfully saved YAML file to {save_yaml_path}")
            except Exception as e:
                logger.error(f"Error saving YAML file: {str(e)}")
                raise

        return yaml_dict

    except Exception as e:
        logger.error(f"Unexpected error in create_yaml_from_pandas_df: {str(e)}")
        raise



# def create_yaml_from_pandas_df(df, folder_path, yaml_name):
#     """Create YAML file from pandas DataFrame"""
#     try:
#         # Ensure the directory exists
#         os.makedirs(folder_path, exist_ok=True)
        
#         # Convert DataFrame to list of dictionaries
#         records = df.to_dict(orient='records')
        
#         # Create the YAML structure
#         yaml_data = {
#             'models': {}
#         }
        
#         # Group by model_id
#         for record in records:
#             model_id = record['model_id']
#             if model_id not in yaml_data['models']:
#                 yaml_data['models'][model_id] = {
#                     'name': record['model_name'],
#                     'config': record['model_config'],
#                     'trainer_name': record['model_trainer_name'],
#                     'postprocess': record['model_postprocess'],
#                     'map': {}
#                 }
#             # Add map information
#             yaml_data['models'][model_id]['map'][record['mapid']] = record['structure_name']
        
#         # Write to YAML file
#         yaml_path = os.path.join(folder_path, yaml_name)
#         with open(yaml_path, 'w') as file:
#             yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False)
            
#     except Exception as e:
#         print(f"Error creating YAML file: {str(e)}")
#         raise