import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from . import tasks
from .models import LemmyCommunity, RedditAccount, RedditSubmission

logger = logging.getLogger(__name__)


@receiver(post_save, sender=RedditAccount)
def on_reddit_account_created_make_mirror(sender, **kw):
    if kw["created"] and not kw["raw"]:
        reddit_account = kw["instance"]
        reddit_account.register_mirror()


@receiver(post_save, sender=RedditSubmission)
def on_reddit_submission_created_post_to_lemmy_communities(sender, **kw):
    if kw["created"] and not kw["raw"]:
        reddit_submission = kw["instance"]
        if not reddit_submission.can_be_submitted_automatically:
            return

        lemmy_communities = LemmyCommunity.objects.filter(
            reddittolemmycommunity__subreddit=reddit_submission.subreddit
        )

        for lemmy_community in lemmy_communities:
            if lemmy_community.can_accept_automatic_submission(reddit_submission):
                tasks.mirror_reddit_submission.delay(
                    reddit_submission_id=reddit_submission.id,
                    lemmy_community_id=lemmy_community.id,
                )
