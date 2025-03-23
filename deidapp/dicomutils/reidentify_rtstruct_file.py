import os
import uuid
import pydicom
import pandas as pd
import logging
from datetime import date
from django.conf import settings
from deidapp.models import DicomSeries, DicomInstance, RTStructFile

# Configure logger
logger = logging.getLogger('deidapp')

def reidentify_rtstruct_files(source_dir=None, target_dir=None):
    """
    Reidentify RTStruct files from source directory and save to target directory.
    
    Parameters:
    -----------
    source_dir : str, optional
        Source directory containing deidentified RTSTRUCT files.
        Defaults to 'folder_deidentified_rtstruct' under MEDIA_ROOT.
    target_dir : str, optional
        Target directory for reidentified RTSTRUCT files.
        Defaults to 'folder_identified_rtstruct' under MEDIA_ROOT.
        
    Returns:
    --------
    dict
        Dictionary containing counts of processed files and errors.
    """
    # Set default directories if not provided
    if source_dir is None:
        source_dir = os.path.join(settings.MEDIA_ROOT, 'folder_deidentified_rtstruct')
    if target_dir is None:
        target_dir = os.path.join(settings.MEDIA_ROOT, 'folder_identified_rtstruct')
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    logger.info(f"Target directory: {target_dir}")
    
    # Process all files in the source directory
    processed_count = 0
    error_count = 0
    
    # Walk through directory and subdirectories
    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            file_path = os.path.join(root, filename)
            logger.info(f"Processing file: {file_path}")
            
            try:
                # Step 1: Check if file is valid DICOM
                try:
                    ds = pydicom.dcmread(file_path)
                except:
                    logger.warning(f"Invalid DICOM file: {file_path}")
                    continue

                # Step 2: Check if modality is RTSTRUCT
                if not hasattr(ds, 'Modality') or ds.Modality != 'RTSTRUCT':
                    logger.info(f"Not a RTSTRUCT file: {file_path}")
                    continue

                # Step 3: Get Referenced Series Instance UID
                found_series_instance_uid = None
                
                def get_referenced_series_uid(ds, elem):
                    nonlocal found_series_instance_uid
                    if elem.tag == (0x0020, 0x000E):
                        logger.debug(f"Found Referenced Series Instance UID: {elem.value}")
                        found_series_instance_uid = elem.value
                
                ds.walk(get_referenced_series_uid)
                
                deidentified_series_instance_uid = found_series_instance_uid
                logger.info(f"Deidentified Series Instance UID: {deidentified_series_instance_uid}")

                if deidentified_series_instance_uid is None:
                    logger.warning(f"Could not find Referenced Series Instance UID in: {file_path}")
                    continue

                # Get all series with matching series instance UID
                matching_series = DicomSeries.objects.filter(
                    deidentified_series_instance_uid=deidentified_series_instance_uid
                )

                if not matching_series.exists():
                    logger.warning(f"No matching DICOM Series Found: {file_path}")
                    continue

                # Log the number of matching series found
                logger.info(f"Found {matching_series.count()} series with matching Series Instance UID")
                
                series = matching_series.first()
                logger.info(f"Series: {series}")
                logger.info(f"Selected series with UID: {series.series_instance_uid}")

                # Step 4 & 5: Get required values from DicomStudy and Patient models
                study = series.study
                logger.info(f"Study: {study}")
                patient = study.patient
                logger.info(f"Patient: {patient}")

                # Step 5: Replace basic DICOM tags with original values
                ds.StudyInstanceUID = study.study_instance_uid
                logger.info(f"Study Instance UID: {ds.StudyInstanceUID}")
                ds.PatientID = patient.patient_id
                logger.info(f"Patient ID: {ds.PatientID}")
                ds.PatientName = patient.patient_name
                logger.info(f"Patient Name: {ds.PatientName}")
                ds.StudyDescription = study.study_description
                logger.info(f"Study Description: {ds.StudyDescription}")
                ds.PatientBirthDate = patient.patient_birth_date.strftime('%Y%m%d')
                logger.info(f"Patient Birth Date: {ds.PatientBirthDate}")
                ds.ReferringPhysicianName = "DRAW"
                ds.AccessionNumber = "202514789"                    

                # Step 6: Create dataframe of all UIDs
                instances = DicomInstance.objects.filter(series=series)
                logger.info(f"Instances: {instances}")
                # Collect all UIDs (instance, series, and study level)
                df_data = {
                    'original_id': (
                        # Instance level UIDs
                        [inst.sop_instance_uid for inst in instances] +
                        # Series level UIDs
                        [series.series_instance_uid] +
                        # Study level UIDs
                        [study.study_instance_uid]
                    ),
                    'deidentified_id': (
                        # Instance level UIDs
                        [inst.deidentified_sop_instance_uid for inst in instances] +
                        # Series level UIDs
                        [series.deidentified_series_instance_uid] +
                        # Study level UIDs
                        [study.deidentified_study_instance_uid]
                    )
                }

                df = pd.DataFrame(df_data)
                logger.debug("Reference DataFrame created")
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"DataFrame content:\n{df}")

                # Step 7: Replace all UIDs using callbacks
                replacement_count = 0
                
                def frame_of_reference_callback(ds, elem):
                    """Replace Frame of Reference UIDs"""
                    if elem.tag in [(0x0020,0x0052), (0x3006,0x0024)]:
                        elem.value = series.frame_of_reference_uid

                def sop_instance_callback(ds, elem):
                    """Replace Referenced SOP Instance UIDs"""
                    nonlocal replacement_count
                    if elem.tag == (0x0008,0x1155):  # Referenced SOP Instance UID
                        deidentified_id = elem.value
                        matching_row = df[df['deidentified_id'] == deidentified_id]
                        if not matching_row.empty:
                            elem.value = matching_row.iloc[0]['original_id']
                            replacement_count += 1
                
                ds.walk(frame_of_reference_callback)
                ds.walk(sop_instance_callback)
                
                logger.info(f"Number of SOP Instance UID replacements: {replacement_count}")

                # Step 8: Save the updated file with unique name directly to target_dir
                base_name, extension = os.path.splitext(filename)
                unique_filename = f"{base_name}_{str(uuid.uuid4())[:8]}{extension}"
                output_path = os.path.join(target_dir, unique_filename)
                ds.save_as(output_path)
                logger.info(f"Saved reidentified file: {output_path}")

                # Step 9: Update or create RTStructFile record
                rtstruct_file, created = RTStructFile.objects.update_or_create(
                    series_instance_uid=ds.SeriesInstanceUID,
                    original_file_path=file_path,
                    defaults={
                        'dicom_series': series,
                        'processed_file_path': output_path,
                        'processing_date': date.today(),
                        'processing_status': 'SUCCESS'
                    }
                )
                logger.info(f"Updated database record for RTStructFile: {rtstruct_file.series_instance_uid}")
                processed_count += 1

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
                error_count += 1
                # Update database with error status
                try:
                    RTStructFile.objects.update_or_create(
                        series_instance_uid=ds.SeriesInstanceUID if 'ds' in locals() else 'UNKNOWN',
                        original_file_path=file_path,
                        defaults={
                            'dicom_series': series if 'series' in locals() else None,
                            'processing_date': date.today(),
                            'processing_status': f'ERROR: {str(e)}'
                        }
                    )
                except Exception as db_error:
                    logger.error(f"Error updating database: {str(db_error)}", exc_info=True)
                    
            logger.info(f"Completed processing of {file_path}")

    logger.info(f"Finished processing all files. Processed: {processed_count}, Errors: {error_count}")
    return {
        'processed_count': processed_count,
        'error_count': error_count
    }

