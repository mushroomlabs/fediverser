import datetime
import logging

from celery import shared_task

from .models import RedditCommunity, RedditSubmission

logger = logging.getLogger(__name__)


@shared_task
def fetch_new_posts(subreddit_name):
    NOW = datetime.datetime.now()
    THRESHOLD = NOW - datetime.timedelta(hours=12)

    try:
        subreddit = RedditCommunity.objects.get(name=subreddit_name)
        latest_run = subreddit.most_recent_post or THRESHOLD
        for post in [p for p in subreddit.new() if p.created_utc > latest_run.timestamp()]:
            RedditSubmission.make(subreddit=subreddit, post=post)
    except RedditCommunity.DoesNotExist:
        logger.warning("Subreddit not found", extra={"name": subreddit_name})


@shared_task
def update_all_subreddits():
    for subreddit_name in RedditCommunity.objects.values_list("name", flat=True):
        fetch_new_posts.delay(subreddit_name=subreddit_name)
