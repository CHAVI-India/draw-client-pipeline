import logging
import pydicom
import zipfile
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta
from django.utils import timezone
from api_client.models import DicomTransfer, SystemSettings
from api_client.api_utils.dicom_export import DicomExporter
from django.conf import settings

logger = logging.getLogger('api_client')

def compute_file_checksum(file_path):
    """
    Compute SHA-256 checksum of a file.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read the file in chunks to handle large files efficiently
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def scan_dicom_folder(delta_time=10):
    """
    Scan the designated DICOM folder for series folders.
    If all files in a folder are older than 10 minutes, zip the folder contents.
    """
    try:
        # Create dicom_folder if it doesn't exist
        dicom_folder = Path(os.path.join(settings.BASE_DIR, 'folder_post_deidentification'))
        if not os.path.exists(dicom_folder):
            os.makedirs(dicom_folder, exist_ok=True)
        temp_folder = Path(os.path.join(settings.BASE_DIR, 'folder_temp'))
        if not os.path.exists(temp_folder):
            os.makedirs(temp_folder, exist_ok=True)
        archive_folder = Path(os.path.join(settings.BASE_DIR, 'folder_archive'))
        if not os.path.exists(archive_folder):
            os.makedirs(archive_folder, exist_ok=True)
        
        if not all(os.path.exists(folder) for folder in [dicom_folder, temp_folder, archive_folder]):
            logger.error("One or more required folders do not exist")
            return
        
        # Get current time for comparison
        current_time = timezone.now()
        cutoff_time = current_time - timedelta(minutes=delta_time)

        # Scan only immediate subdirectories (series folders)
        for series_folder in dicom_folder.iterdir():
            if not series_folder.is_dir():
                continue

            # Get all files in the series folder
            all_files = list(series_folder.glob('*.*'))
            if not all_files:
                continue
            
            # Check if there are any DICOM files to read metadata from
            dicom_files = [f for f in all_files if f.suffix.lower() == '.dcm']
            if not dicom_files:
                logger.warning(f"No DICOM files found in {series_folder}, skipping")
                continue
                
            logger.info(f"Found {len(all_files)} total files in {series_folder}")
            
            # Check modification times of all files
            all_files_old = all(
                datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.get_current_timezone()) <= cutoff_time
                for f in all_files
            )

            if not all_files_old:
                continue

            try:
                # Read first DICOM file to get UIDs
                first_dicom = dicom_files[0]
                ds = pydicom.dcmread(str(first_dicom), stop_before_pixels=True)
                series_uid = ds.SeriesInstanceUID
                study_uid = ds.StudyInstanceUID

                # Get client name from settings
                system_settings = SystemSettings.load()
                client_name = system_settings.client_id
                # Sanitize client name for use in filename
                client_name = client_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                client_name = ''.join(c for c in client_name if c.isalnum() or c in '_-')
                
                # Create zip file with client name and series UID
                zip_path = temp_folder / f"{client_name}_{series_uid}.zip"
                try:
                    logger.info(f"Creating zip file at {zip_path} with {len(all_files)} files")
                    
                    # First verify all files are readable
                    valid_files = []
                    for file_path in all_files:
                        try:
                            with open(file_path, 'rb') as f:
                                f.seek(0, 2)
                                size = f.tell()
                                if size == 0:
                                    logger.warning(f"Skipping empty file: {file_path}")
                                    continue
                                valid_files.append((file_path, size))
                        except Exception as e:
                            logger.error(f"Error reading file {file_path}: {e}")
                            continue
                    
                    if not valid_files:
                        raise ValueError("No valid files found to add to zip")
                    
                    logger.info(f"Found {len(valid_files)} valid files to zip")
                    
                    # Create zip with validated files
                    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                        for file_path, size in valid_files:
                            arcname = file_path.name
                            #logger.debug(f"Adding file to zip: {file_path} ({size} bytes) as {arcname}")
                            with open(file_path, 'rb') as f:
                                content = f.read()
                                zf.writestr(arcname, content)
                        
                        # Verify zip contents
                        zip_info = zf.infolist()
                        total_size = sum(info.file_size for info in zip_info)
                        logger.info(f"Created zip with {len(zip_info)} files, total size: {total_size} bytes")
                        
                        # Test zip integrity
                        test_result = zf.testzip()
                        if test_result is not None:
                            raise zipfile.BadZipFile(f"Corrupt zip file detected at {test_result}")
                        logger.info("Zip file integrity test passed")

                    # Final verification
                    if not zip_path.exists():
                        raise ValueError(f"Zip file was not created at {zip_path}")
                    
                    zip_size = zip_path.stat().st_size
                    if zip_size == 0:
                        raise ValueError(f"Created zip file is empty: {zip_path}")
                    
                    logger.info(f"Successfully created zip file: {zip_path} (size: {zip_size} bytes)")

                    # Compute checksum after creating zip
                    zip_checksum = compute_file_checksum(zip_path)
                    logger.info(f"Computed checksum for {zip_path}: {zip_checksum}")

                    # Initiate transfer with checksum
                    exporter = DicomExporter()
                    exporter.initiate_transfer(
                        str(zip_path),
                        study_uid,
                        series_uid,
                        zip_checksum
                    )
                    logger.info(f"Initiated transfer for series {series_uid}")

                    # Move processed files to archive
                    series_archive = archive_folder / study_uid / series_uid
                    series_archive.mkdir(parents=True, exist_ok=True)
                    for file_path in all_files:
                        new_path = series_archive / file_path.name
                        try:
                            # Check if destination file already exists
                            if new_path.exists():
                                # Either remove the existing file or skip this file
                                logger.warning(f"Destination file already exists: {new_path}")
                                # Option 1: Remove existing file before moving
                                new_path.unlink()
                                file_path.rename(new_path)
                                # Option 2: Skip this file (uncomment if preferred)
                                # logger.warning(f"Skipping file: {file_path}")
                                # continue
                            else:
                                file_path.rename(new_path)
                        except Exception as e:
                            logger.error(f"Error moving file {file_path} to {new_path}: {str(e)}")
                            # Continue with other files even if one fails

                    # Remove the now empty series folder
                    if not any(series_folder.iterdir()):
                        series_folder.rmdir()

                except Exception as e:
                    logger.error(f"Error processing series folder {series_folder}: {str(e)}")
                    if zip_path.exists():
                        zip_path.unlink()

            except Exception as e:
                logger.error(f"Error reading DICOM file {first_dicom}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in scan_dicom_folder: {str(e)}")
