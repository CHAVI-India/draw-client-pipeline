
# from draw_tracker.models import copyDicom
import os
import shutil
from datetime import datetime, timezone
from dicom_handler.models import CopyDicom
from django.utils import timezone


def copydicom(sourcedir, destinationdir, timeinterval): 
    '''
    copy scan dicom shared network dir to destinationdir
    '''
    for dir in os.listdir(sourcedir):
        dicom_dir = os.path.join(sourcedir, dir)
        print(dicom_dir)
        if os.path.isdir(dicom_dir):
            dir_size = os.path.getsize(dicom_dir)
            print(dir_size)
            created_date = timezone.make_aware(
                datetime.fromtimestamp(os.path.getctime(dicom_dir)),
                timezone=timezone.get_current_timezone()
            )
            print(created_date)
            modified_date = timezone.make_aware(
                datetime.fromtimestamp(os.path.getmtime(dicom_dir)),
                timezone=timezone.get_current_timezone()
            )

            if modified_date.date() == datetime.today().date():  # time taken from database modal 

                destination_dir = os.path.join(destinationdir, dir)
                existing_dir = CopyDicom.objects.filter(
                    sourcedirname = dicom_dir,
                    dirmodifieddate = modified_date
                )
                if not existing_dir:
                    try:
                        shutil.copytree(
                            dicom_dir,
                            destination_dir
                            
                        )
                        CopyDicom(
                            sourcedirname = dicom_dir,
                            destinationdirname = destination_dir,
                            dircreateddate = created_date,
                            dirmodifieddate = modified_date,
                            dirsize = dir_size
                        ).save()
                        print(f"Created new copyDicom object for {dir}")
                    except Exception as e:
                        print(e)

                else:
                    print(f"Matching object already exists for {dir}")
    
    return 
