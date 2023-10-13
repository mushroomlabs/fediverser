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
        "update-subreddits": {
            "task": "fediverser.apps.core.tasks.update_all_subreddits",
            "schedule": crontab(minute="*/2"),
        },
        "update-comments": {
            "task": "fediverser.apps.core.tasks.fetch_new_comments",
            "schedule": crontab(minute="*/3"),
        },
        "push-to-lemmy": {
            "task": "fediverser.apps.core.tasks.push_updates_to_lemmy",
            "schedule": crontab(minute="*/2"),
        },
    }

    task_always_eager = settings.TEST_MODE
    task_eager_propagates = settings.TEST_MODE


app = Celery()
app.config_from_object(FediverserCeleryConfig)
app.autodiscover_tasks()
