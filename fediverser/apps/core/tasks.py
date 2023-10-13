import datetime
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from .choices import AutomaticSubmissionPolicies
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
def mirror_reddit_submission(reddit_submission_id, lemmy_community_id):
    try:
        reddit_submission = RedditSubmission.objects.get(id=reddit_submission_id)
        lemmy_community = LemmyCommunity.objects.get(id=lemmy_community_id)

        reddit_submission.post_to_lemmy(lemmy_community)
    except RedditSubmission.DoesNotExist:
        logger.exception("Reddit Submission not found in database")
    except LemmyCommunity.DoesNotExist:
        logger.exception("Lemmy Community not recorded")


@shared_task
def mirror_reddit_comment(reddit_comment_id, mirrored_post_id):
    try:
        comment = RedditComment.objects.get(id=reddit_comment_id)
        mirrored_post = LemmyMirroredPost.objects.get(id=mirrored_post_id)
        comment.make_mirror(mirrored_post=mirrored_post)

    except RedditComment.DoesNotExist:
        logger.exception("Reddit comment not found in database")
    except LemmyMirroredPost.DoesNotExist:
        logger.exception("Lemmy mirrored post not recorded")


@shared_task
def fetch_new_posts(subreddit_name):
    NOW = timezone.now()
    THRESHOLD = NOW - datetime.timedelta(hours=12)

    try:
        subreddit = RedditCommunity.objects.get(name=subreddit_name)
        latest_run = subreddit.most_recent_post or THRESHOLD
        for post in [p for p in subreddit.new() if p.created_utc > latest_run.timestamp()]:
            RedditSubmission.make(subreddit=subreddit, post=post)
    except RedditCommunity.DoesNotExist:
        logger.warning("Subreddit not found", extra={"name": subreddit_name})


@shared_task
def fetch_new_comments():
    NOW = timezone.now()

    mirrored_submissions = RedditSubmission.objects.filter(
        lemmy_mirrored_posts__isnull=False
    ).annotate(most_recent_mirrored_comment=Max("lemmy_mirrored_posts__comments__modified"))

    old_post = Q(created__lte=NOW - datetime.timedelta(hours=12))
    new_post = Q(created__gte=NOW - datetime.timedelta(minutes=3))
    fresh_comment = Q(most_recent_mirrored_comment__gte=NOW - datetime.timedelta(minutes=3))

    for reddit_submission in mirrored_submissions.exclude(old_post | new_post | fresh_comment):
        RedditSubmission.make(
            subreddit=reddit_submission.subreddit, post=reddit_submission.praw_object
        )


@shared_task
def update_all_subreddits():
    for subreddit_name in RedditCommunity.objects.values_list("name", flat=True):
        fetch_new_posts.delay(subreddit_name=subreddit_name)


@shared_task
def push_updates_to_lemmy():
    NOW = timezone.now()

    NO_MIRROR_ALLOWED = AutomaticSubmissionPolicies.NONE
    submissions = (
        RedditSubmission.objects.filter()
        .annotate(mirrors=Count("lemmy_mirrored_posts"))
        .annotate(latest_comment=Max("comments__created"))
        .annotate(latest_mirror=Max("lemmy_mirrored_posts__comments__created"))
    )

    unmapped = Q(subreddit__reddittolemmycommunity__isnull=True)
    old_post = Q(created__lte=NOW - datetime.timedelta(days=1))
    automatic_mirror_disallowed = Q(
        subreddit__reddittolemmycommunity__automatic_submission_policy=NO_MIRROR_ALLOWED
    )
    from_spammer = Q(author__marked_as_spammer=True)
    from_bot = Q(author__marked_as_bot=True)

    unpostable = unmapped | automatic_mirror_disallowed | from_spammer | from_bot | old_post

    for reddit_submission in submissions.exclude(unpostable):
        has_mirrors = reddit_submission.mirrors > 0
        last_commented_at = reddit_submission.latest_comment
        last_mirrored_at = reddit_submission.latest_mirror

        if not reddit_submission.can_be_submitted_automatically:
            continue

        if last_commented_at is None and has_mirrors:
            continue

        if last_commented_at is not None and last_mirrored_at is not None:
            if last_commented_at <= last_mirrored_at:
                continue

        lemmy_communities = LemmyCommunity.objects.filter(
            reddittolemmycommunity__subreddit=reddit_submission.subreddit
        )

        for lemmy_community in lemmy_communities:
            if lemmy_community.can_accept_automatic_submission(reddit_submission):
                try:
                    reddit_submission.post_to_lemmy(lemmy_community)
                except Exception:
                    logger.exception(f"Failed to post {reddit_submission.id}")
            else:
                logger.info(f"Not posting {reddit_submission.id} to {lemmy_community.name}")
