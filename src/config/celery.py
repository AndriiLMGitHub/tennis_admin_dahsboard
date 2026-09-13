import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")


app.conf.imports = [
    'infrastructure.email.tasks',
    'infrastructure.r2_storage.tasks',
]

# Schedule
app.conf.beat_schedule = {
    'cleanup-orphaned-r2-files-every-night': {
        'task': 'infrastructure.r2_storage.tasks.clear_orphaned_r2_uploads',
        'schedule': crontab(hour=3, minute=0),
    },
}