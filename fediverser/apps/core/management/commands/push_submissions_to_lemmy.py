import datetime
import logging
import time

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from fediverser.apps.core.choices import AutomaticSubmissionPolicies
from fediverser.apps.core.exceptions import LemmyClientRateLimited, RejectedPost
from fediverser.apps.core.models import LemmyCommunity, RedditSubmission

logger = logging.getLogger(__name__)


def push_new_submissions_to_lemmy():
    NOW = timezone.now()

    is_retrieved = Q(status=RedditSubmission.STATUS.retrieved)
    allows_automatic_mirroring = Q(
        subreddit__reddittolemmycommunity__automatic_submission_policy__in=[
            AutomaticSubmissionPolicies.FULL,
            AutomaticSubmissionPolicies.SELF_POST_ONLY,
            AutomaticSubmissionPolicies.LINK_ONLY,
        ]
    )

    unmapped = Q(subreddit__reddittolemmycommunity__isnull=True)
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

        lemmy_communities = [
            community
            for community in LemmyCommunity.objects.filter(
                reddittolemmycommunity__subreddit=reddit_submission.subreddit
            )
            if community.can_accept_automatic_submission(reddit_submission)
        ]

        if len(lemmy_communities) == 0:
            reddit_submission.status = RedditSubmission.STATUS.rejected
            reddit_submission.save()
            continue

        for lemmy_community in lemmy_communities:
            try:
                reddit_submission.post_to_lemmy(lemmy_community)
                logger.info(f"Posted {reddit_submission.id} to {lemmy_community.name}")
            except RejectedPost as exc:
                logger.warning(f"Post was rejected: {exc}")
                reddit_submission.status = RedditSubmission.STATUS.rejected
                reddit_submission.save()
            except Exception:
                logger.exception(f"Failed to post {reddit_submission.id}")


class Command(BaseCommand):
    help = "Continuously push comments and posts to mirror lemmy communities"

    def handle(self, *args, **options):
        while True:
            time.sleep(1)
            try:
                push_new_submissions_to_lemmy()
            except LemmyClientRateLimited:
                logger.warning("Lemmy client is being rate-limited")
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Keyboard Interrupt. Exiting")
                break
