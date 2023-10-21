import logging

from allauth.socialaccount.signals import social_account_added
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


@receiver(social_account_added)
def on_reddit_user_connected_account_update_lemmy_mirror(sender, **kw):
    social_login = kw["sociallogin"]

    if social_login.account.provider == "reddit":
        reddit_username = social_login.account.extra_data["name"]
        RedditAccount.objects.update_or_create(
            username=reddit_username, defaults={"controller": social_login.account.user}
        )
