import logging

from django.conf import settings

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

from ...api_utils import (
    scan_dicom_folder,
    poll_pending_transfers,
    notify_completed_transfers,
    cleanup_old_transfers
)

logger = logging.getLogger(__name__)

# The `close_old_connections` decorator ensures that database connections, that have become
# unusable or are obsolete, are closed before and after your job has run. You should use it
# to wrap any jobs that you schedule that access the Django database in any way. 
@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """
    This job deletes APScheduler job execution entries older than `max_age` from the database.
    It helps to prevent the database from filling up with old historical records that are no
    longer useful.
    
    :param max_age: The maximum length of time to retain historical job execution records.
                    Defaults to 7 days.
    """
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            scan_dicom_folder,
            trigger=IntervalTrigger(minutes=1),
            id='scan_dicom_folder',
            max_instances=1,
            replace_existing=True
        )
        
        scheduler.add_job(
            poll_pending_transfers,
            trigger=IntervalTrigger(minutes=10),
            id='poll_pending_transfers',
            max_instances=1,
            replace_existing=True
        )
        
        scheduler.add_job(
            notify_completed_transfers,
            trigger=IntervalTrigger(minutes=5),
            id='notify_completed_transfers',
            max_instances=1,
            replace_existing=True
        )
        
        scheduler.add_job(
            cleanup_old_transfers,
            trigger=CronTrigger(hour=0),  # Run at midnight
            id='cleanup_old_transfers',
            max_instances=1,
            replace_existing=True
        )    

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
                day_of_week="mon", hour="00", minute="00"
            ),  # Midnight on Monday, before start of the next work week.
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(
            "Added weekly job: 'delete_old_job_executions'."
        )

        try:
            logger.info("Starting scheduler...")
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.shutdown()
            logger.info("Scheduler shut down successfully!")