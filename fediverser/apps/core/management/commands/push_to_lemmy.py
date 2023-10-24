import datetime
import logging
import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone

from fediverser.apps.core.choices import AutomaticSubmissionPolicies
from fediverser.apps.core.exceptions import LemmyClientRateLimited, RejectedComment, RejectedPost
from fediverser.apps.core.models import (
    LemmyCommunity,
    LemmyMirroredComment,
    RedditComment,
    RedditCommunity,
    RedditSubmission,
)

logger = logging.getLogger(__name__)


def push_new_comments_to_lemmy():
    for subreddit in RedditCommunity.objects.filter(reddittolemmycommunity__isnull=False):
        mirrored_comments = LemmyMirroredComment.objects.filter(
            lemmy_mirrored_post__reddit_submission__subreddit=subreddit
        )

        most_recent = mirrored_comments.aggregate(most_recent=Max("created")).get("most_recent")
        threshold = most_recent or timezone.now() - datetime.timedelta(minutes=10)
        candidates = RedditComment.objects.filter(
            created__gte=threshold,
            submission__subreddit=subreddit,
            status=RedditComment.STATUS.retrieved,
        )

        with_mirrored_submissions = Q(submission__lemmy_mirrored_posts__isnull=False)
        no_pending_parent = Q(parent=None) | Q(parent__status=RedditComment.STATUS.mirrored)

        comments_pending = candidates.filter(with_mirrored_submissions).filter(no_pending_parent)

        for comment in comments_pending.distinct().iterator():
            for mirrored_post in comment.submission.lemmy_mirrored_posts.all():
                try:
                    community_name = mirrored_post.lemmy_community.name
                    comment.make_mirror(mirrored_post=mirrored_post, include_children=False)

                except RejectedComment as exc:
                    logger.warning(f"Comment is rejected: {exc}")
                    comment.status = RedditComment.STATUS.rejected
                    comment.save()

                except LemmyClientRateLimited:
                    logger.warning("Too many requests. Will stop pushing submissions to Lemmy")
                    return

                except Exception:
                    logger.exception(f"Failed to mirror comment {comment.id} to {community_name}")


def push_new_submissions_to_lemmy():
    NOW = timezone.now()

    NO_MIRROR_ALLOWED = AutomaticSubmissionPolicies.NONE

    unmapped = Q(subreddit__reddittolemmycommunity__isnull=True)
    old_post = Q(created__lte=NOW - datetime.timedelta(days=1))

    already_posted = Q(lemmy_mirrored_posts__isnull=False)
    automatic_mirror_disallowed = Q(
        subreddit__reddittolemmycommunity__automatic_submission_policy=NO_MIRROR_ALLOWED
    )
    from_spammer = Q(author__marked_as_spammer=True)
    from_bot = Q(author__marked_as_bot=True)

    submissions = RedditSubmission.objects.filter(
        status=RedditSubmission.STATUS.retrieved
    ).exclude(
        unmapped
        | automatic_mirror_disallowed
        | from_spammer
        | from_bot
        | old_post
        | already_posted
    )

    for reddit_submission in submissions.distinct():
        if not reddit_submission.can_be_submitted_automatically:
            continue

        lemmy_communities = LemmyCommunity.objects.filter(
            reddittolemmycommunity__subreddit=reddit_submission.subreddit
        )

        for lemmy_community in lemmy_communities:
            if lemmy_community.can_accept_automatic_submission(reddit_submission):
                try:
                    reddit_submission.post_to_lemmy(lemmy_community)
                    logger.info(f"Posted {reddit_submission.id} to {lemmy_community.name}")
                except RejectedPost as exc:
                    logger.warning(f"Post was rejected: {exc}")
                    reddit_submission.status = RedditSubmission.STATUS.rejected
                    reddit_submission.save()
                except LemmyClientRateLimited:
                    logger.warning("Too many requests. Will stop pushing submissions to Lemmy")
                    return
                except Exception:
                    logger.exception(f"Failed to post {reddit_submission.id}")


class Command(BaseCommand):
    help = "Continuously push comments and posts to mirror lemmy communities"

    def handle(self, *args, **options):
        while True:
            try:
                push_new_comments_to_lemmy()
                push_new_submissions_to_lemmy()
                time.sleep(1)
            except LemmyClientRateLimited:
                logger.warning("Lemmy client is being rate-limited")
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Keyboard Interrupt. Exiting")
                break
