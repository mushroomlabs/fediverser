import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings


class FediverserCeleryConfig(object):
    name = "fediverser"

    broker_url = "memory" if settings.TEST_MODE else settings.CELERY_BROKER_URL
    broker_use_ssl = "FEDIVERSER_BROKER_USE_SSL" in os.environ
    beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
    beat_schedule = {
        "fetch_content_feeds": {
            "task": "fediverser.apps.core.tasks.fetch_feeds",
            "schedule": crontab(),
        },
        "clear_old_feed_entries": {
            "task": "fediverser.apps.core.tasks.clear_old_feed_entries",
            "schedule": crontab(minute=0, hour=0),
        },
        "sync_change_feeds": {
            "task": "fediverser.apps.core.tasks.sync_change_feeds",
            "schedule": crontab(),
        },
        "push_lemmy_submissions": {
            "task": "fediverser.apps.core.tasks.push_new_submissions_to_lemmy",
            "schedule": crontab(),
        },
        "push_lemmy_comments": {
            "task": "fediverser.apps.core.tasks.push_new_comments_to_lemmy",
            "schedule": crontab(),
        },
    }

    task_always_eager = settings.TEST_MODE
    task_eager_propagates = settings.TEST_MODE


app = Celery()
app.config_from_object(FediverserCeleryConfig)
app.autodiscover_tasks()
