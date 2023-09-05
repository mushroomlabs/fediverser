import datetime
import logging

from celery import shared_task

from .models import RedditCommunity, RedditSubmission

logger = logging.getLogger(__name__)


@shared_task
def fetch_new_reddit_posts():
    NOW = datetime.datetime.now()
    THRESHOLD = NOW - datetime.timedelta(hours=12)

    for subreddit in RedditCommunity.objects.all():
        latest_run = subreddit.most_recent_post or THRESHOLD
        for post in [p for p in subreddit.new() if p.created_utc > latest_run.timestamp()]:
            RedditSubmission.make(subreddit=subreddit, post=post)
