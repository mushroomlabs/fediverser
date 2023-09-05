import os

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

TEST_MODE = "FEDIVERSER_TEST" in os.environ


class FediverserCeleryConfig(object):
    name = "fediverser"

    broker_url = "memory" if TEST_MODE else settings.CELERY_BROKER_URL
    broker_use_ssl = "FEDIVERSER_BROKER_USE_SSL" in os.environ
    beat_scheduler = "django_celery_beat.schedulers:DatabaseScheduler"
    beat_schedule = {
        "fetch-new-reddit-posts": {
            "task": "fediverser.apps.core.tasks.fetch_new_reddit_posts",
            "schedule": crontab(minute="*/10"),
        },
    }

    task_always_eager = TEST_MODE
    task_eager_propagates = TEST_MODE


app = Celery()
app.config_from_object(FediverserCeleryConfig)
app.autodiscover_tasks()
