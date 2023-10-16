import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import RedditAccount
from .tasks import clone_redditor

logger = logging.getLogger(__name__)


@receiver(post_save, sender=RedditAccount)
def on_reddit_account_created_make_mirror(sender, **kw):
    if kw["created"] and not kw["raw"]:
        reddit_account = kw["instance"]
        clone_redditor.delay(reddit_account.username)
