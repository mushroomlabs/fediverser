import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .exceptions import LemmyClientRateLimited, RejectedComment
from .models import (
    LemmyCommunity,
    LemmyCommunityInvite,
    LemmyCommunityInviteTemplate,
    LemmyMirroredPost,
    RedditAccount,
    RedditComment,
    RedditCommunity,
    RedditSubmission,
    make_reddit_client,
)

logger = logging.getLogger(__name__)


@shared_task
def post_mirror_disclosure(mirrored_post_id):
    try:
        mirrored_post = LemmyMirroredPost.objects.get(id=mirrored_post_id)
        mirrored_post.submit_disclosure_comment()
    except LemmyMirroredPost.DoesNotExist:
        logger.warning("Could not find mirrored post")


@shared_task
def clone_redditor(reddit_username, as_bot=True):
    try:
        reddit_account = RedditAccount.objects.get(username=reddit_username)
        reddit_account.register_mirror(as_bot=as_bot)
    except RedditAccount.DoesNotExist:
        logger.warning("Could not find reddit account")


@shared_task
def subscribe_to_lemmy_community(reddit_username, lemmy_community_id):
    try:
        reddit_account = RedditAccount.objects.get(username=reddit_username)
        assert (
            reddit_account.is_initial_password_in_use
        ), "Account is taken over by owner, can not do anything on their behalf"

        lemmy_community = LemmyCommunity.objects.get(id=lemmy_community_id)
        lemmy_client = reddit_account.make_lemmy_client()
        community_id = lemmy_client.discover_community(lemmy_community.fqdn)
        lemmy_client.community.follow(community_id)
    except RedditAccount.DoesNotExist:
        logger.warning("Could not find reddit account")

    except AssertionError as exc:
        logger.warning(str(exc))


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


@shared_task
def mirror_comment_to_lemmy(comment_id):
    try:
        comment = RedditComment.objects.get(id=comment_id, status=RedditComment.STATUS.accepted)
    except RedditComment.DoesNotExist:
        logger.warning(f"Comment {comment_id} not found or not accepted for scheduling")
        return

    for mirrored_post in comment.submission.lemmy_mirrored_posts.all():
        community_name = mirrored_post.lemmy_community.name
        try:
            comment.make_mirror(mirrored_post=mirrored_post, include_children=False)

        except RejectedComment as exc:
            logger.warning(f"Comment is rejected: {exc}")
            comment.status = RedditComment.STATUS.rejected
            comment.save()

        except LemmyClientRateLimited:
            logger.warning("Too many requests. Need to cool down requests to Lemmy")

        except Exception:
            logger.exception(f"Failed to mirror comment {comment_id} to {community_name}")
