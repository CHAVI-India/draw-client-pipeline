import shutil
from dicom_handler.models import DicomPathConfig


# Check yaml file and delete
def check_and_delete_yaml(folder_path):
    """
    Check for YAML files in a given folder and delete them
    
    Args:
        folder_path (str): Path to the folder to check
        
    Returns:
        None
    """
    import os
    import glob
    
    yaml_files = glob.glob(os.path.join(folder_path, "*.yml"))     
    for yaml_file in yaml_files:
        try:
            os.remove(yaml_file)
            print(f"Deleted YAML file: {yaml_file}")
        except OSError as e:
            print(f"Error deleting {yaml_file}: {e}")



# Move a folder destination directory
def move_folder_with_yaml_check(unprocess_dir, copy_yaml):
    
    # unprocess_dir = DicomPathConfig.objects.values("dicomnonprocessedfolderpath").first()["dicomnonprocessedfolderpath"]
    processing_dir = DicomPathConfig.objects.values("dicomprocessingfolderpath").first()["dicomprocessingfolderpath"]
    check_and_delete_yaml(folder_path=unprocess_dir)
    shutil.copy2(copy_yaml, unprocess_dir)
    shutil.move(unprocess_dir, processing_dir)

    