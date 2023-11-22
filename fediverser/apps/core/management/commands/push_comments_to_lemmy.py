import datetime
import logging
import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone

from fediverser.apps.core.choices import AutomaticCommentPolicies
from fediverser.apps.core.exceptions import LemmyClientRateLimited, RejectedComment
from fediverser.apps.core.models import LemmyMirroredComment, RedditComment, RedditCommunity

logger = logging.getLogger(__name__)


def push_new_comments_to_lemmy():
    allows_automatic_mirroring = Q(
        reddittolemmycommunity__automatic_comment_policy__in=[
            AutomaticCommentPolicies.FULL,
            AutomaticCommentPolicies.SELF_POST_ONLY,
            AutomaticCommentPolicies.LINK_ONLY,
        ]
    )

    mapped = Q(reddittolemmycommunity__isnull=False)

    for subreddit in RedditCommunity.objects.filter(mapped & allows_automatic_mirroring):
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
                logger.info(f"Mirroring comment {comment.id}")
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
            else:
                logger.info(f"Comment {comment.id} is pending but post has not been mirrored yet.")


class Command(BaseCommand):
    help = "Continuously push comments to mirror lemmy communities"

    def handle(self, *args, **options):
        while True:
            try:
                push_new_comments_to_lemmy()
            except LemmyClientRateLimited:
                logger.warning("Lemmy client is being rate-limited")
                time.sleep(30)
            except KeyboardInterrupt:
                logger.info("Keyboard Interrupt. Exiting")
                break
