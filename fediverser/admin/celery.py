import os

from celery import Celery
from django.conf import settings

TEST_MODE = "FEDIVERSER_TEST" in os.environ


class FediverserCeleryConfig(object):
    name = "fediverser"

    broker_url = "memory" if TEST_MODE else settings.CELERY_BROKER_URL
    broker_use_ssl = "FEDIVERSER_BROKER_USE_SSL" in os.environ
    beat_schedule = {}

    task_always_eager = TEST_MODE
    task_eager_propagates = TEST_MODE


app = Celery()
app.config_from_object(FediverserCeleryConfig)
app.autodiscover_tasks()
