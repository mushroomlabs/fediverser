import datetime
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from fediverser.apps.lemmy.services import LemmyClientRateLimited, LocalUserProxy

from .choices import AutomaticSubmissionPolicies
from .models.activitypub import Community
from .models.feeds import Entry, Feed
from .models.invites import CommunityInvite, CommunityInviteTemplate
from .models.mirroring import LemmyMirroredComment, LemmyMirroredPost
from .models.reddit import (
    RedditAccount,
    RedditComment,
    RedditCommunity,
    RedditSubmission,
    RejectedPost,
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
def subscribe_to_community(lemmy_local_user_id, community_id):
    try:
        lemmy_local_user = LocalUserProxy.objects.get(id=lemmy_local_user_id)
        community = Community.objects.get(id=community_id)
        lemmy_client = lemmy_local_user.make_lemmy_client()
        community_id = lemmy_client.discover_community(community.fqdn)
        lemmy_client.community.follow(community_id)
    except LocalUserProxy.DoesNotExist:
        logger.warning("Could not find lemmy user")


def send_community_invite_to_redditor(redditor_name: str, subreddit_name: str):
    try:
        account = RedditAccount.objects.get(username=redditor_name)
        subreddit = RedditCommunity.objects.get(name=subreddit_name)
        community = Community.objects.get(invite_templates__subreddit=subreddit)

        assert settings.REDDIT_BOT_ACCOUNT_USERNAME is not None, "reddit bot is not set up"
        assert settings.REDDIT_BOT_ACCOUNT_PASSWORD is not None, "reddit bot has no password"

        reddit = make_reddit_client(
            username=settings.REDDIT_BOT_ACCOUNT_USERNAME,
            password=settings.REDDIT_BOT_ACCOUNT_PASSWORD,
        )

    except (RedditAccount.DoesNotExist, RedditCommunity.DoesNotExist, Community.DoesNotExist):
        logger.warning("Could not find target for invite")
        return

    except AssertionError as exc:
        logger.warning(str(exc))
        return

    invite_template = CommunityInviteTemplate.objects.get(community=community, subreddit=subreddit)
    subject = f"Invite to join {community.name} community on Lemmy"

    with transaction.atomic():
        reddit.redditor(redditor_name).message(subject=subject, message=invite_template.message)
        CommunityInvite.objects.create(redditor=account, template=invite_template)


@shared_task
def fetch_new_posts(subreddit_name):
    try:
        subreddit = RedditCommunity.objects.get(name=subreddit_name)
        subreddit.fetch_new_posts()
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
        community_name = mirrored_post.community.name
        try:
            LemmyMirroredComment.make_mirror(
                reddit_comment=comment, mirrored_post=mirrored_post, include_children=False
            )
        except LemmyClientRateLimited:
            logger.warning("Too many requests. Need to cool down requests to Lemmy")

        except Exception:
            logger.exception(f"Failed to mirror comment {comment_id} to {community_name}")


@shared_task
def push_new_submissions_to_lemmy():
    NOW = timezone.now()

    is_retrieved = Q(status=RedditSubmission.STATUS.retrieved)
    allows_automatic_mirroring = Q(
        subreddit__mirroring_strategies__automatic_submission_policy__in=[
            AutomaticSubmissionPolicies.FULL,
            AutomaticSubmissionPolicies.SELF_POST_ONLY,
            AutomaticSubmissionPolicies.LINK_ONLY,
        ]
    )

    unmapped = Q(subreddit__mirroring_strategies__isnull=True)
    old_post = Q(created__lte=NOW - datetime.timedelta(days=1))

    already_posted = Q(lemmy_mirrored_posts__isnull=False)
    from_spammer = Q(author__marked_as_spammer=True)
    from_bot = Q(author__marked_as_bot=True)

    submissions = RedditSubmission.objects.filter(
        is_retrieved & allows_automatic_mirroring
    ).exclude(unmapped | from_spammer | from_bot | old_post | already_posted)

    for reddit_submission in submissions.distinct():
        logger.info(f"Checking submission {reddit_submission.url}")

        if not reddit_submission.can_be_submitted_automatically:
            reddit_submission.status = RedditSubmission.STATUS.rejected
            reddit_submission.save()
            continue

        communities = [
            community
            for community in Community.objects.filter(
                mirroring_strategies__subreddit=reddit_submission.subreddit,
                mirroring_strategies__automatic_submission_policy__in=[
                    AutomaticSubmissionPolicies.FULL,
                    AutomaticSubmissionPolicies.SELF_POST_ONLY,
                    AutomaticSubmissionPolicies.LINK_ONLY,
                ],
            )
        ]

        if len(communities) == 0:
            reddit_submission.status = RedditSubmission.STATUS.rejected
            reddit_submission.save()
            continue

        for community in communities:
            try:
                LemmyMirroredPost.make_mirror(
                    reddit_submission=reddit_submission, community=community
                )
                logger.info(f"Posted {reddit_submission.id} to {community.name}")
            except RejectedPost as exc:
                logger.warning(f"Post was rejected: {exc}")
                reddit_submission.status = RedditSubmission.STATUS.rejected
                reddit_submission.save()
            except Exception:
                logger.exception(f"Failed to post {reddit_submission.id}")


@shared_task
def fetch_feed(feed_url):
    feed = Feed.make(feed_url)
    feed.fetch()


@shared_task
def fetch_feeds():
    for feed in Feed.objects.all():
        feed.fetch()


@shared_task
def clear_old_feed_entries():
    now = timezone.now()
    cutoff = now - Entry.MAX_AGE
    Entry.objects.filter(modified__lte=cutoff).delete()
