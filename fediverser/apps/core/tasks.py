import datetime
import logging

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from .choices import AutomaticSubmissionPolicies
from .models import (
    LemmyCommunity,
    LemmyCommunityInvite,
    LemmyCommunityInviteTemplate,
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
def push_new_comments_to_lemmy():
    comments_pending = RedditComment.objects.filter(
        submission__lemmy_mirrored_posts__isnull=False, lemmy_mirrored_comments__isnull=True
    ).select_related("parent")

    for comment in comments_pending:
        if comment.should_be_mirrored:
            for mirrored_post in comment.submission.lemmy_mirrored_posts.all():
                try:
                    community_name = mirrored_post.lemmy_community.name
                    comment.make_mirror(mirrored_post=mirrored_post, include_children=False)
                    logger.info(f"Posted comment {comment.id} on {community_name}")
                except Exception:
                    logger.exception(f"Failed to mirror comment {comment.id} to {community_name}")


@shared_task
def push_new_submissions_to_lemmy():
    NOW = timezone.now()

    NO_MIRROR_ALLOWED = AutomaticSubmissionPolicies.NONE
    submissions = (
        RedditSubmission.objects.filter()
        .annotate(latest_comment=Max("comments__created"))
        .annotate(latest_mirror=Max("lemmy_mirrored_posts__comments__created"))
    )

    unmapped = Q(subreddit__reddittolemmycommunity__isnull=True)
    old_post = Q(created__lte=NOW - datetime.timedelta(days=1))
    already_posted = Q(lemmy_mirrored_posts__isnull=False)
    automatic_mirror_disallowed = Q(
        subreddit__reddittolemmycommunity__automatic_submission_policy=NO_MIRROR_ALLOWED
    )
    from_spammer = Q(author__marked_as_spammer=True)
    from_bot = Q(author__marked_as_bot=True)

    to_exclude = (
        unmapped
        | automatic_mirror_disallowed
        | from_spammer
        | from_bot
        | old_post
        | already_posted
    )

    for reddit_submission in submissions.exclude(to_exclude):
        last_commented_at = reddit_submission.latest_comment
        last_mirrored_at = reddit_submission.latest_mirror

        if not reddit_submission.can_be_submitted_automatically:
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
                    logger.info(f"Posted {reddit_submission.id} to {lemmy_community.name}")
                except Exception:
                    logger.exception(f"Failed to post {reddit_submission.id}")


@shared_task
def push_updates_to_lemmy():
    push_new_comments_to_lemmy()
    push_new_submissions_to_lemmy()
