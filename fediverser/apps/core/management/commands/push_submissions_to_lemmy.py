import logging
import time

from django.core.management.base import BaseCommand

from fediverser.apps.core.tasks import push_new_submissions_to_lemmy
from fediverser.apps.lemmy.services import LemmyClientRateLimited

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Continuously push comments and posts to mirror lemmy communities"

    def handle(self, *args, **options):
        while True:
            time.sleep(1)
            try:
                push_new_submissions_to_lemmy()
            except LemmyClientRateLimited:
                logger.warning("Lemmy client is being rate-limited")
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Keyboard Interrupt. Exiting")
                break
