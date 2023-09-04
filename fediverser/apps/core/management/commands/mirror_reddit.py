import datetime
import logging

from django.core.management.base import BaseCommand
from django.db.models import Max

from fediverser.apps.core.models import LemmyMirroredPost, RedditSubmission

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Take new posts from all tracked subreddits and posts to related lemmy communities"

    def handle(self, *args, **options):
        NOW = datetime.datetime.now()
        EPOCH = NOW - datetime.timedelta(hours=12)

        last_run = (
            LemmyMirroredPost.objects.aggregate(latest=Max("created")).get("latest") or EPOCH
        )

        reddit_posts = RedditSubmission.objects.filter(created__gte=last_run).select_related(
            "author"
        )

        for reddit_post in reddit_posts:
            reddit_post.make_mirror()
