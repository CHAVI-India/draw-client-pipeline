# # runapscheduler.py
# import logging

# from django.conf import settings

# from apscheduler.schedulers.blocking import BlockingScheduler
# from apscheduler.triggers.cron import CronTrigger
# from django.core.management.base import BaseCommand
# from django_apscheduler.jobstores import DjangoJobStore
# from django_apscheduler.models import DjangoJobExecution
# from django_apscheduler import util
# from dicom_handler.dicomutils.dicomseriesprocessing import read_dicom_metadata


# logger = logging.getLogger(__name__)

# from dicom_handler.models import DicomPathConfig
# from dicom_handler.dicomutils.copydicom import *
# from dicom_handler.dicomutils.dicomseriesprocessing import *
# from dicom_handler.dicomutils.exportrtstruct import *

# # @util.close_old_connections
# # def copy_dicom():
# #   try:
# #     sourcedir = DicomPathConfig.objects.values("datastorepath").first()["datastorepath"]
# #     destinationdir = DicomPathConfig.objects.values("dicomimportfolderpath").first()["dicomimportfolderpath"]
# #     copydicom(
# #         sourcedir = sourcedir,
# #         destinationdir = destinationdir,
# #         timeinterval=60
# #     )
# #   except Exception as e:
# #     print(e)


# # # @util.close_old_connections
# # def dicom_series_separation():
# #   try:
# #     destinationdir = DicomPathConfig.objects.values("dicomimportfolderpath").first()["dicomimportfolderpath"]
# #     processed_dir = DicomPathConfig.objects.values("dicomprocessingfolderpath").first()["dicomprocessingfolderpath"]
# #     dicom_series_separation(
# #         sourcedir=destinationdir,
# #         processeddir=processed_dir
# #     )
# #   except Exception as e:
# #     print(e)


# # # @util.close_old_connections
# # def processing_dicom():
# #   try:
# #     processed_dir = DicomPathConfig.objects.values("dicomprocessingfolderpath").first()["dicomprocessingfolderpath"]
# #     unprocessed_dir = DicomPathConfig.objects.values("dicomnonprocessedfolderpath").first()["dicomnonprocessedfolderpath"]
# #     deidentified_dir = DicomPathConfig.objects.values("deidentificationfolderpath").first()["deidentificationfolderpath"]

# #     for i in os.listdir(processed_dir):
# #        read_dicom_metadata(
# #            dicom_series_path = os.path.join(processed_dir, i),
# #            unprocess_dicom_path=os.path.join(unprocessed_dir, i),
# #            deidentified_dicom_path=os.path.join(deidentified_dir, i)
# #        )
# #   except Exception as e:
# #       print(e)

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
#   help = "Runs APScheduler."

#   def handle(self, *args, **options):
#     scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
#     scheduler.add_jobstore(DjangoJobStore(), "default")

#     # draw dicom
#     scheduler.add_job(
#         draw_dicom,
#         trigger=CronTrigger(minute="*/15"),  # Every 15 Minute
#         id="draw_dicom",  # The `id` assigned to each job MUST be unique
#         max_instances=1,
#         replace_existing=True,
#     )
#     logger.info("Draw dicom done")

#     # Send rtstruct 
#     scheduler.add_job(
#         send_rtstruct,
#         trigger=CronTrigger(minute="*/30"),  # Every 30 Minute
#         id="send_rtstruct",  # The `id` assigned to each job MUST be unique
#         max_instances=1,
#         replace_existing=True,
#     )
#     logger.info("Sending Rtstruct done")

#     # copy dicom
#     # scheduler.add_job(
#     #     copy_dicom,
#     #     trigger=CronTrigger(minute="*/03"),  # Every 05 Minute
#     #     id="copy_dicom",  # The `id` assigned to each job MUST be unique
#     #     max_instances=1,
#     #     replace_existing=True,
#     # )
#     # logger.info("Copy dicom done")


#     # # dicom series separation
#     # scheduler.add_job(
#     #     dicom_series_separation,
#     #     trigger=CronTrigger(minute="*/15"),  # Every 05 Minute
#     #     id="dicom_series_separation",  # The `id` assigned to each job MUST be unique
#     #     max_instances=1,
#     #     replace_existing=True,
#     # )
#     # logger.info("Copy dicom done")

    
#     # # dicom series processing
#     # scheduler.add_job(
#     #     processing_dicom,
#     #     trigger=CronTrigger(minute="*/15"),  # Every 05 Minute
#     #     id="dicom_series_separation",  # The `id` assigned to each job MUST be unique
#     #     max_instances=1,
#     #     replace_existing=True,
#     # )
#     # logger.info("Copy dicom done")


#     scheduler.add_job(
#       delete_old_job_executions,
#       trigger=CronTrigger(
#         day_of_week="mon", hour="00", minute="00"
#       ),  # Midnight on Monday, before start of the next work week.
#       id="delete_old_job_executions",
#       max_instances=1,
#       replace_existing=True,
#     )
#     logger.info(
#       "Added weekly job: 'delete_old_job_executions'."
#     )

#     try:
#       logger.info("Starting scheduler...")
#       scheduler.start()
#     except KeyboardInterrupt:
#       logger.info("Stopping scheduler...")
#       scheduler.shutdown()
#       logger.info("Scheduler shut down successfully!")
