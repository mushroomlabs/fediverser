import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    LemmyCommunity,
    LemmyCommunityInvite,
    LemmyCommunityInviteTemplate,
    RedditAccount,
    RedditCommunity,
    RedditSubmission,
    make_reddit_client,
)

logger = logging.getLogger(__name__)


@shared_task
def clone_redditor(reddit_username):
    try:
        reddit_account = RedditAccount.objects.get(username=reddit_username)
        reddit_account.register_mirror()
    except RedditAccount.DoesNotExist:
        logger.warning("Could not find reddit account")
        return


def send_lemmy_community_invite_to_redditor(redditor_name: str, subreddit_name: str):
    try:
        account = RedditAccount.objects.get(username=redditor_name)
        subreddit = RedditCommunity.objects.get(name=subreddit_name)
        lemmy_community = LemmyCommunity.objects.get(invite_templates__subreddit=subreddit)

        assert settings.REDDIT_BOT_ACCOUNT_USERNAME is not None, "reddit bot is not set up"
        assert settings.REDDIT_BOT_ACCOUNT_PASSWORD is not None, "reddit bot has no password"

        reddit = make_reddit_client(
            username=settings.REDDIT_BOT_ACCOUNT_USERNAME,
            password=settings.REDDIT_BOT_ACCOUNT_PASSWORD,
        )

    except (RedditAccount.DoesNotExist, RedditCommunity.DoesNotExist, LemmyCommunity.DoesNotExist):
        logger.warning("Could not find target for invite")
        return

    except AssertionError as exc:
        logger.warning(str(exc))
        return

    invite_template = LemmyCommunityInviteTemplate.objects.get(
        lemmy_community=lemmy_community, subreddit=subreddit
    )
    subject = f"Invite to join {lemmy_community.name} community on Lemmy"

    with transaction.atomic():
        reddit.redditor(redditor_name).message(subject=subject, message=invite_template.message)
        LemmyCommunityInvite.objects.create(redditor=account, template=invite_template)


@shared_task
def fetch_new_posts(subreddit_name):
    client = make_reddit_client()
    try:
        subreddit = RedditCommunity.objects.get(name=subreddit_name)

        most_recent_post = subreddit.most_recent_post
        posts = [p for p in client.subreddit(subreddit.name).new()]

        if most_recent_post is not None:
            posts = [p for p in posts if p.created_utc > most_recent_post.timestamp()]

        for post in posts:
            RedditSubmission.make(subreddit=subreddit, post=post)

        subreddit.last_synced_at = timezone.now()
        subreddit.save()

    except RedditCommunity.DoesNotExist:
        logger.warning("Subreddit not found", extra={"name": subreddit_name})
