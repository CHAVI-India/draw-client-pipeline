
import pandas as pd
import yaml
import os
import numpy as np
import logging


# Get loggers for different purposes
logger = logging.getLogger('django_log_lens.client')
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
            grouped = df.groupby('model_id').agg({
                'model_name': lambda x: str(x.iloc[0]).replace("'", "").strip(), 
                'model_config': lambda x: str(x.iloc[0]).replace("'", "").strip(),
                'map_tg263_primary_name': lambda x: dict(enumerate(x.tolist(), 1)),
                'model_trainer_name': lambda x: str(x.iloc[0]),
                'model_postprocess': lambda x: str(x.iloc[0]) 
            }).to_dict('index')
            logger.info("Successfully grouped data by model_id")
        except Exception as e:
            logger.error(f"Error during data grouping: {str(e)}")
            raise

        # Create the final structure
        try:
            yaml_dict = {
                'name': data["model_name"].iloc[0],
                'protocol': data["model_name"].iloc[0],
                'models': {
                    model_name: {
                        'name': data["model_name"],
                        'config': data['model_config'],
                        'map': data['map_tg263_primary_name'],
                        'trainer_name': data['model_trainer_name'],
                        'postprocess': data["model_postprocess"]
                    }
                    for model_name, data in grouped.items()
                }
            }
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

        return "yaml_dict"

    except Exception as e:
        logger.error(f"Unexpected error in create_yaml_from_pandas_df: {str(e)}")
        raise