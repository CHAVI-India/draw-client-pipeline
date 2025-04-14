import pandas as pd
import yaml
import os
import numpy as np
import logging


# # Get loggers for different purposes
logger = logging.getLogger('dicom_handler_logs')
# logger = logging.getLogger('django')

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
            # print("Grouped data:")
            # print(grouped)

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
            # print("YAML dictionary:")
            # print(yaml_dict)
            logger.info("Successfully created YAML dictionary structure")
        except Exception as e:
            logger.error(f"Error creating YAML dictionary: {str(e)}")
            raise

        # Save to file if path is provided
        if save_yaml_path is not None:
            try:
                # Normalize the path to prevent path traversal attacks
                normalized_base_path = os.path.abspath(save_yaml_path)
                safe_yaml_name = os.path.basename(yaml_name)  # Extract just the filename
                full_save_path = os.path.normpath(os.path.join(normalized_base_path, safe_yaml_name))
                
                # Verify the normalized path is still within the intended directory
                if not full_save_path.startswith(normalized_base_path):
                    raise ValueError(f"Potential directory traversal attack detected: {yaml_name}")
                
                with open(full_save_path, 'w') as f:
                    yaml.dump(yaml_dict, f, sort_keys=False, default_flow_style=False)
                logger.info(f"Successfully saved YAML file to {full_save_path}")
            except Exception as e:
                logger.error(f"Error saving YAML file: {str(e)}")
                raise

        return yaml_dict

    except Exception as e:
        logger.error(f"Unexpected error in create_yaml_from_pandas_df: {str(e)}")
        raise

