import logging

from django.core.management.base import BaseCommand

from fediverser.apps.core.tasks import fetch_new_reddit_posts

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads new posts from all tracked subreddits"

    def handle(self, *args, **options):
        fetch_new_reddit_posts()
