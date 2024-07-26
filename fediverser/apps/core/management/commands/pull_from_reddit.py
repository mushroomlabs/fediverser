import datetime
import logging
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from fediverser.apps.core.choices import AutomaticCommentPolicies, AutomaticSubmissionPolicies
from fediverser.apps.core.models.reddit import (
    RedditComment,
    RedditCommunity,
    RedditSubmission,
    make_reddit_client,
)

logger = logging.getLogger(__name__)

MAX_SUBREDDITS_PER_QUERY = 10
QUERYING_INTERVAL = datetime.timedelta(minutes=3)


def make_ancestor(client, comment, submission):
    has_parent = comment.parent_id.startswith("t1_")
    if not has_parent:
        return None

    parent_comment_id = comment.parent_id.split("_", 1)[-1]

    reddit_parent_comment = RedditComment.objects.filter(id=parent_comment_id).first()
    if reddit_parent_comment is not None:
        return reddit_parent_comment

    parent_comment = client.comment(parent_comment_id)
    grandparent = make_ancestor(client=client, comment=parent_comment, submission=submission)
    return RedditComment.make(submission, comment=parent_comment, parent=grandparent)


def refresh_threads(client, subreddits):
    if not subreddits.exists():
        logger.info("No threads pending refresh")
        return

    subreddits_to_update = subreddits.order_by("last_synced_at")[:MAX_SUBREDDITS_PER_QUERY]
    subreddit_names = subreddits_to_update.values_list("name", flat=True)

    comments = [c for c in client.subreddit("+".join(subreddit_names)).comments()]

    comment_ids = set([c.id for c in comments])

    already_processed = RedditComment.objects.filter(id__in=comment_ids).values_list(
        "id", flat=True
    )
    new_comments = [c for c in comments if c.id not in already_processed]

    subreddit_map = {r.name.lower(): r for r in subreddits}
    for comment in new_comments:
        subreddit = subreddit_map[comment.subreddit.display_name.lower()]
        reddit_submission = RedditSubmission.objects.filter(id=comment.submission.id).first()
        if reddit_submission is None:
            post = client.submission(comment.submission.id)
            RedditSubmission.make(subreddit=subreddit, post=post)
            continue
        parent = make_ancestor(client, comment, reddit_submission)
        RedditComment.make(submission=reddit_submission, comment=comment, parent=parent)

    subreddits.update(last_synced_at=timezone.now())


def refresh_posts(client, subreddits):
    if not subreddits.exists():
        logger.info("No posts pending refresh")
        return

    subreddits_to_update = subreddits.order_by("last_synced_at")[:MAX_SUBREDDITS_PER_QUERY]
    subreddit_names = subreddits_to_update.values_list("name", flat=True)

    posts = [p for p in client.subreddit("+".join(subreddit_names)).new()]

    subreddit_map = {r.name.lower(): r for r in subreddits}
    for post in posts:
        subreddit = subreddit_map[post.subreddit.display_name.lower()]
        RedditSubmission.make(subreddit=subreddit, post=post)
    subreddits.update(last_synced_at=timezone.now())


def refresh_subreddits(client):
    current_time = timezone.now()
    cutoff = current_time - QUERYING_INTERVAL

    mirrored_subreddits = RedditCommunity.objects.filter(mirroring_strategies__isnull=False)
    automated_subreddits = mirrored_subreddits.exclude(
        mirroring_strategies__automatic_submission_policy=AutomaticSubmissionPolicies.NONE
    )

    # If a subreddit has been created and never synced, we set it for sync now.
    automated_subreddits.filter(last_synced_at=None).update(last_synced_at=cutoff)
    subreddits = automated_subreddits.filter(last_synced_at__lt=cutoff)

    post_only_subreddits = subreddits.filter(
        mirroring_strategies__automatic_comment_policy=AutomaticCommentPolicies.NONE
    )
    comment_mirror_subreddits = subreddits.exclude(
        mirroring_strategies__automatic_comment_policy=AutomaticCommentPolicies.NONE
    )

    refresh_posts(client, post_only_subreddits)
    refresh_threads(client, comment_mirror_subreddits)


class Command(BaseCommand):
    help = "Continuously pull comments and posts from tracked subreddits"

    def handle(self, *args, **options):
        client = make_reddit_client()

        while True:
            try:
                refresh_subreddits(client)
                time.sleep(1)
            except Exception:
                logger.exception("Failed to update now")
                time.sleep(QUERYING_INTERVAL.seconds)
            except KeyboardInterrupt:
                logger.info("Keyboard Interrupt. Exiting")
                break
