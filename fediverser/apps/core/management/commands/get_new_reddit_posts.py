import datetime
import logging

from django.core.management.base import BaseCommand

from fediverser.apps.core.models import RedditCommunity, RedditSubmission

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Downloads new posts from all tracked subreddits"

    def handle(self, *args, **options):
        NOW = datetime.datetime.now()
        THRESHOLD = NOW - datetime.timedelta(hours=12)

        for subreddit in RedditCommunity.objects.all():
            latest_run = subreddit.most_recent_post or THRESHOLD
            for post in [p for p in subreddit.new() if p.created_utc > latest_run.timestamp()]:
                RedditSubmission.make(subreddit=subreddit, post=post)
