# import logging
# from django.conf import settings
# from apscheduler.schedulers.background import BackgroundScheduler  # Changed to BackgroundScheduler
# from apscheduler.triggers.cron import CronTrigger
# from apscheduler.triggers.interval import IntervalTrigger
# from django.core.management.base import BaseCommand
# from django_apscheduler.jobstores import DjangoJobStore
# from django_apscheduler.models import DjangoJobExecution
# from django_apscheduler import util
# from dicom_handler.dicomutils.dicomseriesprocessing import read_dicom_metadata
# from django.core.management import call_command
# from api_client.api_utils import (
#     scan_dicom_folder,
#     poll_pending_transfers,
#     notify_completed_transfers,
#     cleanup_old_transfers
# )

# logger = logging.getLogger(__name__)

# from dicom_handler.models import DicomPathConfig
# from dicom_handler.dicomutils.copydicom import *
# from dicom_handler.dicomutils.dicomseriesprocessing import *
# from dicom_handler.dicomutils.exportrtstruct import *


# @util.close_old_connections
# def draw_dicom():
#   try:
#     sourcedir = DicomPathConfig.objects.values("datastorepath").first()["datastorepath"]
#     destinationdir = DicomPathConfig.objects.values("dicomimportfolderpath").first()["dicomimportfolderpath"]
#     copydicom(
#         sourcedir = sourcedir,
#         destinationdir = destinationdir,
#         timeinterval=60
#     )

#     importdir = DicomPathConfig.objects.values("dicomimportfolderpath").first()["dicomimportfolderpath"]
#     processed_dir = DicomPathConfig.objects.values("dicomprocessingfolderpath").first()["dicomprocessingfolderpath"]
#     try:
#       dicom_series_separation(
#           importdir,
#           processed_dir
#       )
#     except Exception as e:
#       print(e)

#     processed_dir = DicomPathConfig.objects.values("dicomprocessingfolderpath").first()["dicomprocessingfolderpath"]
#     unprocessed_dir = DicomPathConfig.objects.values("dicomnonprocessedfolderpath").first()["dicomnonprocessedfolderpath"]
#     deidentified_dir = DicomPathConfig.objects.values("deidentificationfolderpath").first()["deidentificationfolderpath"]

#     for i in os.listdir(processed_dir):
#        read_dicom_metadata(
#            dicom_series_path = os.path.join(processed_dir, i),
#            unprocess_dicom_path=os.path.join(unprocessed_dir, i),
#            deidentified_dicom_path=os.path.join(deidentified_dir, i)
#       )

#   except Exception as e:
#     print(e)


# @util.close_old_connections
# def send_rtstruct():
#   try:
#     rtstruct_path_path =  DicomPathConfig.objects.values("finalrtstructfolderpath").first()["finalrtstructfolderpath"]   
#     datastore_path = DicomPathConfig.objects.values("datastorepath").first()["datastorepath"]
#     find_pred_rt_files(rtstruct_path_path, datastore_path)
#   except Exception as e:
#     print(e)


# # deidentify and reidentify dicom data
# @util.close_old_connections
# def deidentify():
#    try:
#       # call_command('deidentify_dicom', '/home/sougata/Documents/draw-client-with-ddis/draw-client/data')
#       deidentified_dir = DicomPathConfig.objects.values("deidentificationfolderpath").first()["deidentificationfolderpath"]
#       call_command('deidentify_dicom', f"{deidentified_dir}")
#       print("Successfully DICOM data deidentified")

#    except Exception as e:
#       print(e)


# import uuid
# @util.close_old_connections
# def reidentify():
#    try:
#       source_dir = os.path.join(settings.BASE_DIR, "rtstruct")
#       output_dir =  DicomPathConfig.objects.values("finalrtstructfolderpath").first()["finalrtstructfolderpath"]
#       for i in get_all_files(output_dir):
#         if i.endswith(".dcm"):
#           ds = pydicom.dcmread(i)
#           sop = ds.SOPInstanceUID
#           shutil.copy2(
#             i,
#             os.path.join(source_dir, f"{sop}-{os.path.basename(i)}")  #os.path.basename(i)
#           )
#       target_dir = DicomPathConfig.objects.values("finalrtstructfolderpath").first()["finalrtstructfolderpath"]
#       target_dir = os.path.join(target_dir, "output", "results")

#       call_command('reidentify_rtstructure', f"{source_dir}", f"{target_dir}")
#       print("Reidentify done")

#    except Exception as e:
#       print(e)


# # The `close_old_connections` decorator ensures that database connections, that have become
# # unusable or are obsolete, are closed before and after your job has run. You should use it
# # to wrap any jobs that you schedule that access the Django database in any way. 

# @util.close_old_connections
# def delete_old_job_executions(max_age=604_800):
#   """
#   This job deletes APScheduler job execution entries older than `max_age` from the database.
#   It helps to prevent the database from filling up with old historical records that are no
#   longer useful.
  
#   :param max_age: The maximum length of time to retain historical job execution records.
#                   Defaults to 7 days.
#   """
#   DjangoJobExecution.objects.delete_old_job_executions(max_age)


# class Command(BaseCommand):
#     help = "Runs APScheduler."

#     def handle(self, *args, **options):
#         scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)  # Use BackgroundScheduler
#         scheduler.add_jobstore(DjangoJobStore(), "default")

#         # dicom handler app
#         scheduler.add_job(
#             draw_dicom,
#             trigger=CronTrigger(minute="*/15"),  # Every 15 minutes
#             id="Dicom Series Preparation",
#             max_instances=1,
#             replace_existing=True,
#         )
#         logger.info("Draw dicom job added.")

#         scheduler.add_job(
#             send_rtstruct,
#             trigger=CronTrigger(minute="*/30"),  # Every 30 minutes
#             id="Send Rtstruct to Data Store",
#             max_instances=1,
#             replace_existing=True,
#         )
#         logger.info("Send rtstruct job added.")

#         # deidentify app
#         scheduler.add_job(
#             deidentify,
#             trigger=CronTrigger(minute="*/02"),  
#             id="Deidentify Dicom",
#             max_instances=1,
#             replace_existing=True,
#         )
#         logger.info("deidentify job added.")

#         scheduler.add_job(
#             reidentify,
#             trigger=CronTrigger(minute="*/02"),  
#             id="Reidentify Dicom Rtstruct",
#             max_instances=1,
#             replace_existing=True,
#         )

#         logger.info("reidentify job added.")

#         # api client app
#         scheduler.add_job(
#             scan_dicom_folder,
#             trigger=IntervalTrigger(minutes=1),
#             id='Send Dicom data to remote server',
#             max_instances=1,
#             replace_existing=True
#         )
        
#         scheduler.add_job(
#             poll_pending_transfers,
#             trigger=IntervalTrigger(minutes=10),
#             id='Check Dicom status on remote server',
#             max_instances=1,
#             replace_existing=True
#         )
        
#         scheduler.add_job(
#             notify_completed_transfers,
#             trigger=IntervalTrigger(minutes=5),
#             id='Notify remote server after completed transfers',
#             max_instances=1,
#             replace_existing=True
#         )
        
#         scheduler.add_job(
#             cleanup_old_transfers,
#             trigger=CronTrigger(hour=0),  # Run at midnight
#             id='Cleanup old transfers',
#             max_instances=1,
#             replace_existing=True
#         )    

#         scheduler.add_job(
#             delete_old_job_executions,
#             trigger=CronTrigger(day_of_week="mon", hour="00", minute="00"),  # Every Monday at midnight
#             id="delete_old_job_executions",
#             max_instances=1,
#             replace_existing=True,
#         )
#         logger.info("Delete old job executions job added.")

#         try:
#             logger.info("Starting scheduler...")
#             scheduler.start()  # Start the background scheduler
#         except KeyboardInterrupt:
#             logger.info("Stopping scheduler...")
#             scheduler.shutdown()
#             logger.info("Scheduler shut down successfully!")
