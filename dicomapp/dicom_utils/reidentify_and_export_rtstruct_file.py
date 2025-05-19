import os
import uuid
import pydicom
import pandas as pd
import logging
import re
from datetime import date, datetime
from django.conf import settings
from deidapp.models import *
from dicomapp.models import *
import shutil
from uuid import UUID
# Configure logger
logger = logging.getLogger(__name__)

def mask_phi(text):
    """
    Masks Protected Health Information (PHI) in log messages.
    
    For UIDs: Preserves first 4 and last 4 characters, masks middle with ****
    For dates: Replaces with [DATE REDACTED]
    For names/IDs: Masks completely with [PHI REDACTED]
    """
    if not text or not isinstance(text, str):
        return text
        
    # For UIDs (long numeric/dot strings)
    if re.match(r'^[\d\.]+$', text) and len(text) > 10:
        return f"{text[:4]}****{text[-4:]}"
    
    # For dates in format YYYYMMDD or YYYY-MM-DD or similar
    if re.match(r'^(19|20)\d\d[-/]?[01]\d[-/]?[0-3]\d$', text):
        return "[DATE REDACTED]"
    
    # For patient names, IDs, etc.
    return "[PHI REDACTED]"

def reidentify_rtstruct_file_and_export_to_datastore(dict):
    """
    Reidentify RTStruct files from source paths and save to target directory.
    
    This function processes RTSTRUCT DICOM files by:
    1. Replacing deidentified DICOM tags with their original values
    2. Updating UID references to match the original series
    3. Moving the reidentified files to their final destination
    4. Updating various database models to track the processing status
    
    Processing Flow:
    ---------------
    1. Initial Setup:
       - Creates target directory for reidentified files
       - Initializes counters and result lists
    
    2. For each RTSTRUCT file:
       a. Validation:
          - Checks if file is valid DICOM
          - Verifies if file is already successfully processed
          - Confirms file is an RTSTRUCT modality
          - Extracts Referenced Series Instance UID
          - Finds matching DicomSeries record
       
       b. Reidentification:
          - Updates basic DICOM tags (StudyInstanceUID, PatientID, etc.)
          - Creates mapping of original and deidentified UIDs
          - Replaces UIDs in the RTSTRUCT file using callbacks
       
       c. File Operations:
          - Saves reidentified file with unique name
          - Updates RTStructFile record
          - Updates DicomSeriesProcessingModel status
          - Creates DicomSeriesProcessingLogModel entry
       
       d. Export:
          - Moves file to datastore directory
          - Updates CopyDicomTaskModel with new directory info
          - Updates processing status to RTSTRUCT_EXPORTED
          - Creates export log entry
    
    Conditional Flow:
    ----------------
    File Processing:
    - If file is invalid DICOM: Skips file and continues to next
    - If not RTSTRUCT modality: Skips file and continues to next
    - If no matching series found: Skips file and continues to next
    - If processing fails: Updates RTStructFile with error status
    - Deletes the deidentified RTSTRUCT file
    
    Datastore Directory Operations:
    - If datastore directory doesn't exist:
        * Creates directory
        * Moves file to directory
        * Updates processing status to RTSTRUCT_EXPORTED
        * Updates CopyDicomTaskModel with new directory info
        * Creates export log entry
    - If datastore directory exists:
        * Moves file to directory
        * Updates processing status to RTSTRUCT_EXPORTED
        * Updates CopyDicomTaskModel with new directory info
        * Creates export log entry
    - If export fails:
        * Updates processing status to RTSTRUCT_EXPORT_FAILED
        * Updates series state to FAILED
        * Creates error log entry
        * Continues to next file
    
    Parameters:
    -----------
    dict : dict
        Dictionary containing:
        - rtstruct_paths: list of RTSTRUCT file paths to process
        - status: overall status of the polling operation
        - message: descriptive message about the operation

    Returns:
    --------
    dict
        Dictionary containing:
        - processed_count: number of successfully processed files
        - error_count: number of files that failed processing
        - processed_paths: list of paths to successfully processed and reidentified RTSTRUCT files
        - original_paths: list of original file paths that were successfully processed
        - rtstruct_file_ids: list of series_instance_uids of successfully processed RTStructFile objects
        - failed_paths: list of file paths that failed processing
        - error_messages: list of error messages corresponding to failed files
    """
    # Initialize results
    logger.info(f"Reidentifying RTSTRUCT files")

    processed_count = 0
    error_count = 0
    processed_paths = []  # List to store successfully processed file paths
    original_paths = []   # List to store original file paths
    rtstruct_file_ids = []  # List to store RTStructFile primary keys
    failed_paths = []     # List to store paths of failed files
    error_messages = []   # List to store error messages for failed files
    
    # Get list of file paths to process
    file_paths = dict.get('rtstruct_paths', [])
    logger.info(f"Number of files to process: {len(file_paths)}. File paths: {file_paths}")
    
    # Set target directory
    target_dir = os.path.join(settings.BASE_DIR, 'folders', 'folder_identified_rtstruct')
    
    # Create target directory if it doesn't exist
    os.makedirs(target_dir, exist_ok=True)
    logger.info(f"Target directory: {target_dir}")
    
    # Process each file path
    for file_path in file_paths:
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

            # Step 3: Get Referenced Series Instance UID from the RTSTRUCT file
            referenced_series_uid = None
            for ref_series in ds.ReferencedFrameOfReferenceSequence[0].RTReferencedStudySequence[0].RTReferencedSeriesSequence:
                referenced_series_uid = ref_series.SeriesInstanceUID
                break

            if referenced_series_uid is None:
                logger.warning(f"Could not find Referenced Series Instance UID in: {file_path}")
                continue

            logger.info(f"Found Referenced Series Instance UID: {mask_phi(referenced_series_uid)}")

            # Get all series with matching series instance UID
            matching_series = DicomSeries.objects.filter(
                deidentified_series_instance_uid=referenced_series_uid
            )

            if not matching_series.exists():
                logger.warning(f"No matching DICOM Series Found: {file_path}")
                continue

            # Log the number of matching series found
            logger.info(f"Found {matching_series.count()} series with matching Series Instance UID")
            
            series = matching_series.first()
            logger.info(f"Series: {series}")
            logger.info(f"Selected series with UID: {mask_phi(series.series_instance_uid)}")

            # Step 4 & 5: Get required values from DicomStudy and Patient models
            study = series.study
            logger.info(f"Study: {study}")
            patient = study.patient
            logger.info(f"Patient: {patient}")

            # Step 5: Replace basic DICOM tags with original values
            ds.StudyInstanceUID = study.study_instance_uid
            logger.info(f"Study Instance UID: {mask_phi(ds.StudyInstanceUID)}")
            ds.PatientID = patient.patient_id
            logger.info(f"Patient ID: {mask_phi(ds.PatientID)}")
            ds.PatientName = patient.patient_name
            logger.info(f"Patient Name: {mask_phi(ds.PatientName)}")
            ds.StudyDescription = study.study_description
            logger.info(f"Study Description: {mask_phi(ds.StudyDescription)}")
            ds.PatientBirthDate = patient.patient_birth_date.strftime('%Y%m%d')
            logger.info(f"Patient Birth Date: {mask_phi(ds.PatientBirthDate)}")
            ds.StudyDate = study.study_date.strftime('%Y%m%d')
            logger.info(f"Study Date: {mask_phi(ds.StudyDate)}")
            ds.SeriesDate = series.series_date.strftime('%Y%m%d')
            logger.info(f"Series Date: {mask_phi(ds.SeriesDate)}")
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
                # Don't log the actual DataFrame content as it contains PHI
                logger.debug(f"DataFrame created with {len(df)} rows")

            # Step 7: Replace all UIDs using callbacks
            replacement_count = 0
            
            def frame_of_reference_callback(ds, elem):
                """Replace Frame of Reference UIDs"""
                if elem.tag in [(0x0020,0x0052), (0x3006,0x0024)]:
                    elem.value = series.frame_of_reference_uid

            def sop_instance_callback(ds, elem):
                """Replace Referenced SOP Instance UIDs"""
                nonlocal replacement_count
                if elem.tag in [(0x0008,0x1155), (0x0020,0x000E)]:  # Referenced SOP Instance UID and Reference Series Instance UID replacements
                    deidentified_id = elem.value
                    matching_row = df[df['deidentified_id'] == deidentified_id]
                    if not matching_row.empty:
                        elem.value = matching_row.iloc[0]['original_id']
                        replacement_count += 1
            
            ds.walk(frame_of_reference_callback)
            ds.walk(sop_instance_callback)
            
            logger.info(f"Number of SOP Instance UID replacements: {replacement_count}")

            # Step 8: Save the updated file with unique name directly to the target directory
            base_name, extension = os.path.splitext(os.path.basename(file_path))
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
            logger.info(f"Updated database record for RTStructFile: {mask_phi(rtstruct_file.series_instance_uid)}")

            # From the DicomSeries object we will get the dicom_series_processing_id

            logger.info(f"Starting to update the DicomSeriesProcessingModel and DicomSeriesProcessingLogModel objects")
            try:
                dicom_series_processing_id = series.dicom_series_processing_id
                logger.info(f"Dicom Series Processing ID: {dicom_series_processing_id}")

                # Retreive the DicomSeriesProcessingModel object matching the dicom_series_processing_id
                dicom_series_processing_model = DicomSeriesProcessingModel.objects.get(id=UUID(dicom_series_processing_id))
                logger.info(f"Dicom Series Processing Model: {dicom_series_processing_model}")

                # Update the processing_status field of the DicomSeriesProcessingModel object to RTSTRUCT_REIDENTIFIED and the corresponding DicomSeriesProcessingLogModel object to RTSTRUCT_REIDENTIFIED
                dicom_series_processing_model.processing_status = 'RTSTRUCT_REIDENTIFIED'
                dicom_series_processing_model.save()
                logger.info(f"Updated processing status of DicomSeriesProcessingModel: {dicom_series_processing_id}")

                # Create a new DicomSeriesProcessingLogModel object with the same dicom_series_processing_id and processing_status 'RTSTRUCT_REIDENTIFIED'
                DicomSeriesProcessingLogModel.objects.create(
                    dicom_series_processing_id=dicom_series_processing_model,
                    processing_status='RTSTRUCT_REIDENTIFIED',
                    processing_status_message=f"RTSTRUCT file reidentified successfully"
                )
                logger.info(f"Created new DicomSeriesProcessingLogModel: {dicom_series_processing_id}")
                logger.info(f"Completed updating the DicomSeriesProcessingModel and DicomSeriesProcessingLogModel objects")
            except Exception as e:
                logger.warning(f"Dicom Series Processing Model not updated for series: {mask_phi(series.series_instance_uid)} because of error: {str(e)}", exc_info=True)
                # continue to the next file.
                continue    
            # Delete the deidentified RTSTRUCT file
            os.remove(file_path)
            logger.info(f"Deleted deidentified RTSTRUCT file: {file_path}")
            # Move to the datastore directory
            logger.info(f"Starting to move the reidentified RTSTRUCT file to the datastore directory")

            try:
                #  Get the datastore directory path from the CopyDicomTaskModel object referenced by the DicomSeriesProcessingModel object
                copy_dicom_task_model = dicom_series_processing_model.copy_dicom_task_id
                logger.info(f"Copy DICOM Task Model: {copy_dicom_task_model}")
                datastore_directory_path = copy_dicom_task_model.source_directory
                logger.info(f"Datastore Directory Path: {datastore_directory_path}")
                # If the directory does not exist, create it and then move the file
                if not os.path.exists(datastore_directory_path):
                    try:
                        os.makedirs(datastore_directory_path, exist_ok=True)
                        logger.info(f"Created datastore directory: {datastore_directory_path}")

                        # Use simple copy instead of copy2 to avoid permission issues with metadata
                        destination_path = os.path.join(datastore_directory_path, unique_filename)
                        try:
                            # First try with copy file to avoid permission issues with metadata
                            shutil.copyfile(output_path, destination_path)
                        except PermissionError:
                            # If that fails, try with simple copy
                            logger.warning("Failed to copy with metadata. File is shaved in reidentified RTSTRUCT file.")
                            
                        # Remove the source file after successful copy
                        os.remove(output_path)
                        logger.info(f"Copied and removed reidentified RTSTRUCT file to datastore directory: {destination_path}")

                        # Update the DicomSeriesProcessingModel and DicomSeriesProcessingLogModel objects to RTSTRUCT_EXPORTED
                        dicom_series_processing_model.processing_status = 'RTSTRUCT_EXPORTED'
                        dicom_series_processing_model.series_state = 'COMPLETE'
                        dicom_series_processing_model.save()
                        logger.info(f"Updated processing status of DicomSeriesProcessingModel: {dicom_series_processing_id}")

                        # Create a new DicomSeriesProcessingLogModel object with the same dicom_series_processing_id and processing_status 'RTSTRUCT_EXPORTED'
                        DicomSeriesProcessingLogModel.objects.create(
                            dicom_series_processing_id=dicom_series_processing_model,
                            processing_status='RTSTRUCT_EXPORTED',
                            processing_status_message=f"RTSTRUCT file exported successfully"
                        )
                        logger.info(f"Created new DicomSeriesProcessingLogModel: {dicom_series_processing_id}")

                        # Update the CopyDicomTaskModel object's source_directory modification date to the current date and time.
                        # Compute the size of the source directory and update the source_directory_size field of the CopyDicomTaskModel object.
                        source_directory_size = sum(os.path.getsize(os.path.join(datastore_directory_path, f)) for f in os.listdir(datastore_directory_path) if os.path.isfile(os.path.join(datastore_directory_path, f)))
                        copy_dicom_task_model.source_directory_size = source_directory_size
                        copy_dicom_task_model.source_directory_modification_date = datetime.now()
                        copy_dicom_task_model.save()
                        logger.info(f"Updated source directory modification date of CopyDicomTaskModel: {copy_dicom_task_model.id}")

                    except Exception as e:
                        logger.warning(f"Error moving reidentified RTSTRUCT file to datastore directory: {str(e)}", exc_info=True)
                        # Update the DicomSeriesProcessingModel and DicomSeriesProcessingLogModel objects to RTSTRUCT_EXPORT_FAILED
                        dicom_series_processing_model.processing_status = 'RTSTRUCT_EXPORT_FAILED'
                        dicom_series_processing_model.series_state = 'FAILED'
                        dicom_series_processing_model.save()
                        logger.info(f"Updated processing status of DicomSeriesProcessingModel: {dicom_series_processing_id}")

                        # Create a new DicomSeriesProcessingLogModel object with the same dicom_series_processing_id and processing_status 'RTSTRUCT_EXPORT_FAILED' and processing_status_message 'RTSTRUCT file export failed'
                        DicomSeriesProcessingLogModel.objects.create(
                            dicom_series_processing_id=dicom_series_processing_model,
                            processing_status='RTSTRUCT_EXPORT_FAILED',
                            processing_status_message=f"RTSTRUCT file export failed because of error: {str(e)}"
                        )
                        logger.info(f"Created new DicomSeriesProcessingLogModel: {dicom_series_processing_id}")
                        
                        # continue to the next file.
                        continue

                else:
                    # Directory exists, use simple copy instead of copy2 to avoid permission issues
                    destination_path = os.path.join(datastore_directory_path, unique_filename)
                    try:
                        # First try with copy2
                        shutil.copyfile(output_path, destination_path)
                    except PermissionError:
                        # If that fails, try with simple copy
                        logger.warning("Failed to copy with metadata")

                    # Remove the source file after successful copy
                    os.remove(output_path)
                    logger.info(f"Copied and removed reidentified RTSTRUCT file to datastore directory: {destination_path}")

                    # Update the DicomSeriesProcessingModel and DicomSeriesProcessingLogModel objects to RTSTRUCT_EXPORTED
                    dicom_series_processing_model.processing_status = 'RTSTRUCT_EXPORTED'
                    dicom_series_processing_model.series_state = 'COMPLETE'
                    dicom_series_processing_model.save()
                    logger.info(f"Updated processing status of DicomSeriesProcessingModel: {dicom_series_processing_id}")

                    # Create a new DicomSeriesProcessingLogModel object with the same dicom_series_processing_id and processing_status 'RTSTRUCT_EXPORTED'
                    DicomSeriesProcessingLogModel.objects.create(
                        dicom_series_processing_id=dicom_series_processing_model,
                        processing_status='RTSTRUCT_EXPORTED',
                        processing_status_message=f"RTSTRUCT file exported successfully"
                    )
                    logger.info(f"Created new DicomSeriesProcessingLogModel: {dicom_series_processing_id}")
                    # Update the CopyDicomTaskModel object's source_directory modification date to the current date and time.
                    # Compute the size of the source directory and update the source_directory_size field of the CopyDicomTaskModel object.
                    source_directory_size = sum(os.path.getsize(os.path.join(datastore_directory_path, f)) for f in os.listdir(datastore_directory_path) if os.path.isfile(os.path.join(datastore_directory_path, f)))
                    copy_dicom_task_model.source_directory_size = source_directory_size
                    copy_dicom_task_model.source_directory_modification_date = datetime.now()
                    copy_dicom_task_model.save()
                    logger.info(f"Updated source directory modification date of CopyDicomTaskModel: {copy_dicom_task_model.id}")    
                    
            except Exception as e:
                logger.error(f"Error creating datastore directory: {str(e)}", exc_info=True)
                # Update the DicomSeriesProcessingModel and DicomSeriesProcessingLogModel objects to RTSTRUCT_EXPORT_FAILED
                dicom_series_processing_model.processing_status = 'RTSTRUCT_EXPORT_FAILED'
                dicom_series_processing_model.series_state = 'FAILED'
                dicom_series_processing_model.save()
                logger.info(f"Updated processing status of DicomSeriesProcessingModel: {dicom_series_processing_id}")

                # Create a new DicomSeriesProcessingLogModel object with the same dicom_series_processing_id and processing_status 'RTSTRUCT_EXPORT_FAILED' and processing_status_message 'RTSTRUCT file export failed'
                DicomSeriesProcessingLogModel.objects.create(
                    dicom_series_processing_id=dicom_series_processing_model,
                    processing_status='RTSTRUCT_EXPORT_FAILED',
                    processing_status_message=f"RTSTRUCT file export failed because of error: {str(e)}"
                )
                logger.info(f"Created new DicomSeriesProcessingLogModel: {dicom_series_processing_id}")
                continue

            # Add the successfully processed file path and RTStructFile ID to our lists
            processed_paths.append(str(output_path))
            original_paths.append(str(file_path))
            rtstruct_file_ids.append(rtstruct_file.series_instance_uid)
            logger.info(f"Processed paths added to the list: {processed_paths}")
            logger.info(f"Original paths added to the list: {original_paths}")
            logger.info(f"RTStructFile IDs added to the list: {[mask_phi(id) for id in rtstruct_file_ids]}")

            processed_count += 1

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}", exc_info=True)
            error_count += 1
            failed_paths.append(str(file_path))
            error_messages.append(str(e))
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
    logger.debug(f"Processed paths: {processed_paths}, Original paths: {original_paths}, RTStructFile IDs: {[mask_phi(id) for id in rtstruct_file_ids]}, Failed paths: {failed_paths}")
    return {
        'processed_count': processed_count,
        'error_count': error_count,
        'processed_paths': processed_paths,  # Include the list of processed file paths
        'original_paths': original_paths,    # Include the list of original file paths
        'rtstruct_file_ids': rtstruct_file_ids,  # Include the list of RTStructFile primary keys
        'failed_paths': failed_paths,        # Include the list of failed file paths
        'error_messages': error_messages     # Include the list of error messages
    }

