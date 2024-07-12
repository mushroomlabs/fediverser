import datetime
import logging
import time

from django.core.management.base import BaseCommand
from django.db.models import Max, Q
from django.utils import timezone

from fediverser.apps.core import tasks
from fediverser.apps.core.choices import AutomaticCommentPolicies
from fediverser.apps.core.models import LemmyMirroredComment, RedditComment, RedditCommunity

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Checks and schedules mirroring of comments to lemmy communities"

    def handle(self, *args, **options):
        allows_mirroring = Q(
            mirroring_strategies__automatic_comment_policy__in=[
                AutomaticCommentPolicies.FULL,
                AutomaticCommentPolicies.SELF_POST_ONLY,
                AutomaticCommentPolicies.LINK_ONLY,
            ]
        )

        mapped = Q(mirroring_strategies__isnull=False)

        while True:
            time.sleep(1)
            try:
                for subreddit in RedditCommunity.objects.filter(mapped & allows_mirroring):
                    logger.info(f"Checking comments for {subreddit}")
                    mirrored_comments = LemmyMirroredComment.objects.filter(
                        lemmy_mirrored_post__reddit_submission__subreddit=subreddit
                    )

                    most_recent = mirrored_comments.aggregate(most_recent=Max("created")).get(
                        "most_recent"
                    )
                    threshold = most_recent or timezone.now() - datetime.timedelta(minutes=10)
                    candidates = RedditComment.objects.filter(
                        created__gte=threshold,
                        submission__subreddit=subreddit,
                        status=RedditComment.STATUS.retrieved,
                    )

                    with_mirrored_submissions = Q(submission__lemmy_mirrored_posts__isnull=False)
                    no_pending_parent = Q(parent=None) | Q(
                        parent__status=RedditComment.STATUS.mirrored
                    )

                    comments = candidates.filter(with_mirrored_submissions).filter(
                        no_pending_parent
                    )

                    for comment in comments.distinct().iterator():
                        comment.status = RedditComment.STATUS.accepted
                        comment.save()

                        logger.info(f"Scheduling mirror of comment {comment.id}")
                        tasks.mirror_comment_to_lemmy.delay(comment.id)
                        time.sleep(0.05)

            except KeyboardInterrupt:
                logger.info("Keyboard Interrupt. Exiting")
                break
