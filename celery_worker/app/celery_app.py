import os
import sys
from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# Add the task_parser app to the Python path to share models
sys.path.insert(0, os.path.abspath('/task_parser_app'))

celery_app = Celery(
    "tasks",
    broker=os.environ["CELERY_BROKER_URL"],
    backend=os.environ["CELERY_RESULT_BACKEND"],
    # THIS IS THE PROBLEM:
    include=["tasks.general", "tasks.scheduler"]
)

celery_app.conf.beat_schedule = {
    'run-dispatcher-every-minute': {
        'task': 'dispatch_periodic_tasks',
        'schedule': crontab(), # Runs every minute
    },
}

celery_app.conf.update(
    task_track_started=True,
    timezone='UTC',
    enable_utc=True,
)