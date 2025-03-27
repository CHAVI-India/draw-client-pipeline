import pydicom
import os
import shutil
from deidapp.models import Patient, DicomStudy, DicomSeries, DicomInstance
from dicom_handler.models import DicomUnprocessed
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import random
import time
import calendar
import logging

# Setup logging
logger = logging.getLogger('deidapp')

# Add Celery's logger
celery_logger = logging.getLogger('celery.task')

class DicomDeidentifier:
    def __init__(self):
        # Dictionaries to store mappings of original to deidentified IDs
        self.patient_id_map = {}
        self.study_uid_map = {}
        self.series_uid_map = {}
        self.frame_ref_uid_map = {}
        # Counters for hierarchical UIDs
        self.study_counters = {}  # per patient
        self.series_counters = {}  # per study
        self.instance_counters = {}  # per series
        self.processed_dir = None

    def generate_unique_id(self):
        """Generate a unique ID with the specified format"""
        now = datetime.now()
        random_num = random.randint(100000, 999999)
        unique_id = f"{now.year}.{now.month}.{now.day}.{now.hour}.{now.minute}.{now.second}.{now.microsecond}.{random_num}"
        return unique_id

    def modify_date(self, original_date, date_offset):
        """Modify date by adding the offset while ensuring valid dates"""
        if not original_date:
            return None
        try:
            date_obj = datetime.strptime(original_date, '%Y%m%d')
            
            # Convert days to months and remaining days
            months = date_offset // 30
            remaining_days = date_offset % 30
            
            # First add months using relativedelta (handles month boundaries correctly)
            modified_date = date_obj + relativedelta(months=months)
            # Then add remaining days
            modified_date = modified_date + timedelta(days=remaining_days)
            
            # Ensure year is within valid range
            if modified_date.year < 1900 or modified_date.year > 2100:
                return original_date
            
            return modified_date.strftime('%Y%m%d')
            
        except (ValueError, TypeError):
            return original_date

    def deidentify_dicom(self, ds, date_offset):
        """Deidentify DICOM dataset"""
        # Generate new UIDs
        new_sop_instance_uid = self.generate_unique_id()
        ds.SOPInstanceUID = new_sop_instance_uid
        ds.MediaStorageSOPInstanceUID = new_sop_instance_uid
        ds.StudyInstanceUID = self.generate_unique_id()
        ds.SeriesInstanceUID = self.generate_unique_id()
        if hasattr(ds, 'FrameOfReferenceUID'):
            ds.FrameOfReferenceUID = self.generate_unique_id()
        
        # Modify dates with consistent offset
        if hasattr(ds, 'InstanceCreationDate'):
            ds.InstanceCreationDate = self.modify_date(ds.InstanceCreationDate, date_offset)
        if hasattr(ds, 'StudyDate'):
            ds.StudyDate = self.modify_date(ds.StudyDate, date_offset)
        if hasattr(ds, 'SeriesDate'):
            ds.SeriesDate = self.modify_date(ds.SeriesDate, date_offset)
        if hasattr(ds, 'AcquisitionDate'):
            ds.AcquisitionDate = self.modify_date(ds.AcquisitionDate, date_offset)
        if hasattr(ds, 'ContentDate'):
            ds.ContentDate = self.modify_date(ds.ContentDate, date_offset)
        if hasattr(ds, 'PatientBirthDate'):
            ds.PatientBirthDate = self.modify_date(ds.PatientBirthDate, date_offset)

        # Replace identifying information with '#'
        if hasattr(ds, 'PatientName'):
            ds.PatientName = '#'
        if hasattr(ds, 'ReferringPhysicianName'):
            ds.ReferringPhysicianName = '#'
        if hasattr(ds, 'StudyDescription'):
            ds.StudyDescription = '#'
        if hasattr(ds, 'SeriesDescription'):
            ds.SeriesDescription = '#'
        if hasattr(ds, 'PhysiciansOfRecord'):
            ds.PhysiciansOfRecord = '#'

        # Generate new Patient ID and Study ID
        ds.PatientID = self.generate_unique_id()
        if hasattr(ds, 'StudyID'):
            ds.StudyID = self.generate_unique_id()

        return ds

    def process_dicom_directory(self, dicom_dir, processed_dir):
        """Process a directory of DICOM files for deidentification"""
        self.processed_dir = processed_dir
        
        # Generate a random date offset between -60 and 60 days
        date_offset = random.randint(-60, 60)
        
        # Track the latest patient/study/series info for YAML files
        current_patient_id = None
        current_study_uid = None
        current_series_uid = None
        # Track the series folder for return
        deidentified_series_dir = None

        for root, _, files in os.walk(dicom_dir):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Handle YAML files
                if file.lower().endswith(('.yml', '.yaml')):
                    if current_series_uid:  # We only need series UID now
                        yaml_dest_dir = os.path.join(
                            self.processed_dir,
                            str(current_series_uid)  # Only use series UID
                        )
                        os.makedirs(yaml_dest_dir, exist_ok=True)
                        yaml_dest = os.path.join(yaml_dest_dir, file)
                        shutil.move(file_path, yaml_dest)
                        logger.info(f'Moved YAML file: {file} to series folder')
                    else:
                        # If we don't have context yet, move to processed dir root
                        yaml_dest = os.path.join(self.processed_dir, file)
                        shutil.move(file_path, yaml_dest)
                        logger.warning(f'Moved YAML file: {file} to root (no series context found)')
                    continue

                try:
                    # Try to read the DICOM file
                    ds = pydicom.dcmread(file_path)
                    
                    # Check if modality is one of CT, MRI, or PET
                    modality = getattr(ds, 'Modality', None)
                    if modality not in ['CT', 'MR', 'PT']:
                        logger.warning(f'Deleting {file}: Modality {modality} not in [CT, MR, PT]')
                        os.remove(file_path)
                        continue
                    
                    # Generate deidentified values but don't modify ds yet
                    deidentified_values = self.generate_deidentified_values(ds, date_offset)

                    # Create or get Patient with original values
                    patient, _ = Patient.objects.get_or_create(
                        patient_id=ds.PatientID,
                        defaults={
                            'patient_name': getattr(ds, 'PatientName', None),
                            'patient_birth_date': self.parse_dicom_date(getattr(ds, 'PatientBirthDate', None)),
                            'deidentified_patient_id': deidentified_values['PatientID'],
                            'deidentified_patient_name': '#',
                            'deidentified_patient_birth_date': self.parse_dicom_date(deidentified_values['PatientBirthDate'])
                        }
                    )

                    # Create or get Study with original values
                    study, _ = DicomStudy.objects.get_or_create(
                        study_instance_uid=ds.StudyInstanceUID,
                        defaults={
                            'patient': patient,
                            'study_date': self.parse_dicom_date(getattr(ds, 'StudyDate', None)),
                            'study_description': getattr(ds, 'StudyDescription', None),
                            'study_id': getattr(ds, 'StudyID', None),
                            'deidentified_study_instance_uid': deidentified_values['StudyInstanceUID'],
                            'deidentified_study_date': self.parse_dicom_date(deidentified_values['StudyDate']),
                            'deidentified_study_id': deidentified_values['StudyID']
                        }
                    )

                    # Create or get Series with original values
                    series, _ = DicomSeries.objects.get_or_create(
                        series_instance_uid=ds.SeriesInstanceUID,
                        defaults={
                            'study': study,
                            'series_date': self.parse_dicom_date(getattr(ds, 'SeriesDate', None)),
                            'frame_of_reference_uid': getattr(ds, 'FrameOfReferenceUID', None),
                            'deidentified_series_instance_uid': deidentified_values['SeriesInstanceUID'],
                            'deidentified_series_date': self.parse_dicom_date(deidentified_values['SeriesDate']),
                            'deidentified_frame_of_reference_uid': deidentified_values['FrameOfReferenceUID']
                        }
                    )

                    # Create or get Instance with original values
                    instance, _ = DicomInstance.objects.get_or_create(
                        sop_instance_uid=ds.SOPInstanceUID,
                        defaults={
                            'series': series,
                            'deidentified_sop_instance_uid': deidentified_values['SOPInstanceUID']
                        }
                    )

                    # Now apply the deidentification to the DICOM dataset
                    ds = self.apply_deidentification(ds, deidentified_values)
                    
                    # Remove all private tags. We do not need them in the structure set anyways
                    ds.remove_private_tags()

                    # Create directory structure first
                    new_dir = os.path.join(
                        self.processed_dir,
                        str(ds.SeriesInstanceUID)  # Only use SeriesInstanceUID for directory
                    )
                    os.makedirs(new_dir, exist_ok=True)
                    
                    # Store the series directory for return - THIS IS THE KEY CHANGE
                    deidentified_series_dir = new_dir
                    
                    # Generate a unique filename using original and deidentified UIDs
                    original_sop_uid = instance.sop_instance_uid  # Get the original UID from our database
                    deidentified_sop_uid = ds.SOPInstanceUID
                    filename = f"{deidentified_sop_uid}.dcm"
                    
                    new_file_path = os.path.join(new_dir, filename)
                    ds.save_as(new_file_path, enforce_file_format=True)

                    # Delete the original file
                    os.remove(file_path)

                    logger.info(f'Successfully processed and saved: {file} -> {filename}')

                    # Update current context for YAML files
                    current_patient_id = ds.PatientID
                    current_study_uid = ds.StudyInstanceUID
                    current_series_uid = ds.SeriesInstanceUID

                except pydicom.errors.InvalidDicomError:
                    logger.warning(f'Deleting {file}: Not a valid DICOM file')
                    os.remove(file_path)
                    continue
                except Exception as e:
                    logger.error(f'Error processing {file}: {str(e)}')
                    continue
        
        # Change return to return the series directory instead of a specific file
        if deidentified_series_dir:
            return {
                "status": "success",
                "deidentified_path": deidentified_series_dir
            }
        else:
            return {
                "status": "error",
                "message": "No files were successfully processed"
            }

        # Add cleanup of empty directories after processing all files
        self.cleanup_empty_directories(dicom_dir)
        logger.info('Cleaned up empty directories')

    def parse_dicom_date(self, date_string):
        if not date_string:
            return None
        try:
            return datetime.strptime(date_string, '%Y%m%d').date()
        except ValueError:
            return None

    def generate_deidentified_values(self, ds, date_offset):
        """Generate deidentified values without modifying the dataset"""
        values = {}
        
        try:
            # Reuse or generate new Patient ID
            original_patient_id = ds.PatientID
            
            # Try to get existing mapping from database
            existing_patient = Patient.objects.filter(patient_id=original_patient_id).first()
            
            if existing_patient:
                values['PatientID'] = existing_patient.deidentified_patient_id
                # Initialize study counter for this patient
                self.study_counters[values['PatientID']] = 0
            elif original_patient_id in self.patient_id_map:
                values['PatientID'] = self.patient_id_map[original_patient_id]
            else:
                values['PatientID'] = self.generate_unique_id()
                self.patient_id_map[original_patient_id] = values['PatientID']
                self.study_counters[values['PatientID']] = 0

            # Get or generate Study UID first
            original_study_uid = ds.StudyInstanceUID
            existing_study = DicomStudy.objects.filter(study_instance_uid=original_study_uid).first()
            
            if existing_study:
                values['StudyInstanceUID'] = existing_study.deidentified_study_instance_uid
                values['StudyID'] = existing_study.deidentified_study_id
            elif original_study_uid in self.study_uid_map:
                values['StudyInstanceUID'] = self.study_uid_map[original_study_uid]
                values['StudyID'] = self.study_uid_map.get(f"StudyID_{original_study_uid}")
            else:
                # Generate new study UID for new study
                self.study_counters[values['PatientID']] += 1
                values['StudyInstanceUID'] = f"{values['PatientID']}.{self.study_counters[values['PatientID']]}.0"
                self.study_uid_map[original_study_uid] = values['StudyInstanceUID']
                values['StudyID'] = getattr(ds, 'StudyID', str(self.study_counters[values['PatientID']]))

            # Handle Series UID
            original_series_uid = ds.SeriesInstanceUID
            logger.info(f"\nProcessing series: {original_series_uid}")
            
            # Case 1: Series exists in database - use existing deidentified UID
            existing_series = DicomSeries.objects.filter(series_instance_uid=original_series_uid).first()
            if existing_series:
                values['SeriesInstanceUID'] = existing_series.deidentified_series_instance_uid
                logger.info(f"Using existing series from DB: {values['SeriesInstanceUID']}")
            else:
                # Case 2: New series in existing study - find highest series number and increment
                existing_study_series = DicomSeries.objects.filter(
                    study__deidentified_study_instance_uid=values['StudyInstanceUID']
                ).order_by('-deidentified_series_instance_uid')
                
                if existing_study_series.exists():
                    try:
                        # Get the last series number from the most recent series
                        last_series = existing_study_series.first()
                        last_series_num = int(last_series.deidentified_series_instance_uid.split('.')[-1])
                        next_series_num = last_series_num + 1
                        
                        # Double check this series number isn't already used
                        while DicomSeries.objects.filter(
                            deidentified_series_instance_uid=f"{values['StudyInstanceUID']}.{next_series_num}"
                        ).exists():
                            next_series_num += 1
                            
                        values['SeriesInstanceUID'] = f"{values['StudyInstanceUID']}.{next_series_num}"
                        logger.info(f"Generated incremented series UID: {values['SeriesInstanceUID']}")
                    except (ValueError, IndexError, AttributeError) as e:
                        logger.warning(f"Error parsing series numbers: {e}")
                        values['SeriesInstanceUID'] = f"{values['StudyInstanceUID']}.1"
                else:
                    # Case 3: First series in study
                    values['SeriesInstanceUID'] = f"{values['StudyInstanceUID']}.1"
                    logger.info(f"Generated first series UID: {values['SeriesInstanceUID']}")

            # Generate new SOP Instance UID (always unique per instance)
            values['SOPInstanceUID'] = self.generate_unique_id()
            values['MediaStorageSOPInstanceUID'] = values['SOPInstanceUID']

            # Handle Frame of Reference UID
            if hasattr(ds, 'FrameOfReferenceUID'):
                original_frame_uid = ds.FrameOfReferenceUID
                if original_frame_uid in self.frame_ref_uid_map:
                    values['FrameOfReferenceUID'] = self.frame_ref_uid_map[original_frame_uid]
                else:
                    frame_ref_number = random.randint(1000, 9999)
                    values['FrameOfReferenceUID'] = f"{values['StudyInstanceUID']}.{frame_ref_number}"
                    self.frame_ref_uid_map[original_frame_uid] = values['FrameOfReferenceUID']
            else:
                values['FrameOfReferenceUID'] = None

            # Modify dates
            values['PatientBirthDate'] = self.modify_date(getattr(ds, 'PatientBirthDate', None), date_offset)
            values['StudyDate'] = self.modify_date(getattr(ds, 'StudyDate', None), date_offset)
            values['SeriesDate'] = self.modify_date(getattr(ds, 'SeriesDate', None), date_offset)
            values['InstanceCreationDate'] = self.modify_date(getattr(ds, 'InstanceCreationDate', None), date_offset)
            values['AcquisitionDate'] = self.modify_date(getattr(ds, 'AcquisitionDate', None), date_offset)
            values['ContentDate'] = self.modify_date(getattr(ds, 'ContentDate', None), date_offset)

            return values
            
        except Exception as e:
            logger.error(f"Error in generate_deidentified_values: {str(e)}")
            raise

    def apply_deidentification(self, ds, deidentified_values):
        """Apply deidentification values to the dataset"""
        # Update file meta UIDs
        ds.file_meta.MediaStorageSOPInstanceUID = deidentified_values['SOPInstanceUID']
        
        # Apply UIDs
        ds.SOPInstanceUID = deidentified_values['SOPInstanceUID']
        ds.StudyInstanceUID = deidentified_values['StudyInstanceUID']
        ds.SeriesInstanceUID = deidentified_values['SeriesInstanceUID']
        if hasattr(ds, 'FrameOfReferenceUID') and deidentified_values['FrameOfReferenceUID']:
            ds.FrameOfReferenceUID = deidentified_values['FrameOfReferenceUID']
        
        # Apply dates
        for attr in ['PatientBirthDate', 'StudyDate', 'SeriesDate', 'InstanceCreationDate', 
                    'AcquisitionDate', 'ContentDate']:
            if hasattr(ds, attr) and attr in deidentified_values and deidentified_values[attr]:
                setattr(ds, attr, deidentified_values[attr])
        
        # Apply other deidentification
        ds.PatientID = deidentified_values['PatientID']
        if hasattr(ds, 'StudyID'):
            ds.StudyID = deidentified_values['StudyID']
        
        # Replace or remove identifying information
        if hasattr(ds, 'PatientName'):
            ds.PatientName = "Anonymous"
        if hasattr(ds, 'ReferringPhysicianName'):
            delattr(ds, 'ReferringPhysicianName')
        if hasattr(ds, 'StudyDescription'):
            ds.StudyDescription = f"Study_{deidentified_values['StudyID']}"
        if hasattr(ds, 'SeriesDescription'):
            # Extract series number from SeriesInstanceUID
            series_num = deidentified_values['SeriesInstanceUID'].split('.')[-1]
            ds.SeriesDescription = f"Series_{series_num}"
        if hasattr(ds, 'PhysiciansOfRecord'):
            delattr(ds, 'PhysiciansOfRecord')
            
        return ds

    def cleanup_empty_directories(self, directory):
        """
        Remove empty directories recursively from bottom up, 
        including the series folder itself but not its parent.
        """
        # First, recursively clean up subdirectories
        for root, dirs, files in os.walk(directory, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    # Check if directory is empty (no files and no subdirectories)
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        logger.info(f'Removed empty subdirectory: {dir_path}')
                except OSError as e:
                    logger.warning(f'Error removing directory {dir_path}: {str(e)}')
        
        # Now check if the series folder itself is empty and remove it if so
        try:
            # Check if directory still exists and is empty
            if os.path.exists(directory) and not os.listdir(directory):
                parent_dir = os.path.dirname(directory)
                os.rmdir(directory)
                logger.info(f'Removed empty series folder: {directory}')
        except OSError as e:
            logger.warning(f'Error removing series folder {directory}: {str(e)}')


def process_pending_deidentifications(processed_dir='folder_post_deidentification'):
    """
    Process all DICOM series that are marked as ready for deidentification
    
    Args:
        processed_dir (str): Directory where processed files will be stored.
                            Default is 'folder_post_deidentification'
    
    Returns:
        dict: Summary of processing results
    """
    try:
        # Ensure the processed directory exists
        os.makedirs(processed_dir, exist_ok=True)
        
        # Get series that are ready for deidentification
        series_to_process = DicomUnprocessed.objects.filter(ready_for_deidentification=True)
        logger.info(f"Found {series_to_process.count()} series ready for deidentification")
        
        # Stats to track progress
        results = {
            "total": series_to_process.count(),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": []
        }
        
        # Process each series folder
        for series in series_to_process:
            if not series.series_folder_location or not os.path.exists(series.series_folder_location):
                logger.warning(f"Series folder not found: {series.series_folder_location} for series {series.seriesid}")
                results["skipped"] += 1
                results["details"].append({
                    "series_id": series.seriesid,
                    "status": "skipped",
                    "reason": "Folder not found"
                })
                continue
            
            logger.info(f"Processing series: {series.seriesid} from {series.series_folder_location}")
            
            # Process this individual series
            result = deidentify_dicom(
                dicom_dir=series.series_folder_location,
                processed_dir=processed_dir
            )
            logger.debug(f"Result: {result}")
            
            # Store the result - using correct key name
            detail = {
                "series_id": series.seriesid,
                "status": result["status"],
                "message": result.get("message", "")
            }
            
            # Only add deidentified_path if it exists in the result
            if "deidentified_path" in result:
                detail["deidentified_path"] = result["deidentified_path"]
                
            results["details"].append(detail)
            logger.debug(f"Results: {results}")
            
            # Update series status based on result
            if result["status"] == "success":
                # Mark as processed
                series.ready_for_deidentification = False
                series.series_folder_location = result["deidentified_path"]
                series.save()
                logger.info(f"Successfully processed series: {series.seriesid}")
                results["successful"] += 1
            else:
                logger.error(f"Failed to process series: {series.seriesid} - {result['message']}")
                results["failed"] += 1
        
        results["status"] = "success" if results["failed"] == 0 else "partial"
        results["message"] = f"Processed {results['successful']} series successfully, {results['failed']} failed, {results['skipped']} skipped"

        logger.info(f"Deidentification batch completed: {results['message']}")
        return results
        
    except Exception as e:
        logger.error(f"Error during batch deidentification: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": f"Batch deidentification failed: {str(e)}",
            "error": str(e)
        }

def deidentify_dicom(dicom_dir='folder_for_deidentification', processed_dir='folder_post_deidentification'):
    """
    Deidentify DICOM files in a directory
    
    Args:
        dicom_dir (str): Directory containing DICOM files to process. Default is 'folder_for_deidentification'
        processed_dir (str): Directory where processed files will be stored. Default is 'folder_post_deidentification'
    
    Returns:
        dict: Summary of processing results including deidentified_path (the directory where deidentified files are stored)
    """
    try:
        logger.info(f"Starting DICOM deidentification for: {dicom_dir}")
        
        # Create the processed directory if it doesn't exist
        os.makedirs(processed_dir, exist_ok=True)
        
        # Initialize the deidentifier class
        deidentifier = DicomDeidentifier()
        
        # Process the directory
        result = deidentifier.process_dicom_directory(dicom_dir, processed_dir)
        
        # Clean up empty directories
        deidentifier.cleanup_empty_directories(dicom_dir)
        
        logger.info(f"Completed DICOM deidentification for: {dicom_dir}")
        
        if result.get("status") == "success" and result.get("deidentified_path"):
            logger.info(f"Deidentified files stored in: {result['deidentified_path']}")
            return {
                "status": "success",
                "dicom_dir": dicom_dir, 
                "processed_dir": processed_dir,
                "deidentified_path": result["deidentified_path"],
                "message": "DICOM deidentification completed successfully"
            }
        else:
            error_msg = result.get("message", "Unknown error during deidentification")
            logger.error(f"Deidentification failed: {error_msg}")
            return {
                "status": "error",
                "dicom_dir": dicom_dir,
                "message": error_msg,
                "error": error_msg
            }
        
    except Exception as e:
        logger.error(f"Error during DICOM deidentification: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "dicom_dir": dicom_dir,
            "message": f"DICOM deidentification failed: {str(e)}",
            "error": str(e)
        }