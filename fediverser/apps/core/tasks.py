import datetime
import logging
import time
from contextlib import contextmanager

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from .choices import AutomaticSubmissionPolicies
from .exceptions import LemmyClientRateLimited, RejectedComment
from .models import (
    LemmyCommunity,
    LemmyCommunityInvite,
    LemmyCommunityInviteTemplate,
    LemmyMirroredComment,
    RedditAccount,
    RedditComment,
    RedditCommunity,
    RedditSubmission,
    make_reddit_client,
)

logger = logging.getLogger(__name__)


@contextmanager
def task_mutex(task_key, ttl=30 * 60):
    timeout_at = time.monotonic() + ttl
    status = cache.add(task_key, timeout_at, ttl)
    try:
        yield status
    finally:
        if time.monotonic() < timeout_at and status:
            cache.delete(task_key)


@shared_task
def clone_redditor(reddit_username):
    try:
        reddit_account, _ = RedditAccount.objects.get(username=reddit_username)
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

    except RedditCommunity.DoesNotExist:
        logger.warning("Subreddit not found", extra={"name": subreddit_name})


@shared_task
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


@shared_task
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

    submissions = RedditSubmission.objects.exclude(
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
                except LemmyClientRateLimited:
                    logger.warning("Too many requests. Will stop pushing submissions to Lemmy")
                    return
                except Exception:
                    logger.exception(f"Failed to post {reddit_submission.id}")


@shared_task(bind=True)
def push_updates_to_lemmy(self):
    with task_mutex(self.name) as lock_acquired:
        if lock_acquired:
            push_new_comments_to_lemmy()
            push_new_submissions_to_lemmy()
        else:
            logger.warning("Could not get lock. Skipping this run")


@shared_task(bind=True)
def pull_from_reddit(self):
    client = make_reddit_client()

    subreddit_names = RedditCommunity.objects.values_list("name", flat=True)

    def make_ancestor(comment, submission):
        has_parent = comment.parent_id.startswith("t1_")
        if not has_parent:
            return None

        parent_comment_id = comment.parent_id.split("_", 1)[-1]

        reddit_parent_comment = RedditComment.objects.filter(id=parent_comment_id).first()
        if reddit_parent_comment is not None:
            return reddit_parent_comment

        parent_comment = client.comment(parent_comment_id)
        grandparent = make_ancestor(parent_comment, submission)
        return RedditComment.make(submission, comment=parent_comment, parent=grandparent)

    with task_mutex(self.name) as lock_acquired:
        if lock_acquired:
            all_subreddits = "+".join(subreddit_names)
            comments = [c for c in client.subreddit(all_subreddits).comments()]

            comment_ids = set([c.id for c in comments])

            already_processed = RedditComment.objects.filter(id__in=comment_ids).values_list(
                "id", flat=True
            )
            new_comments = [c for c in comments if c.id not in already_processed]

            for comment in new_comments:
                try:
                    subreddit = RedditCommunity.objects.get(
                        name__iexact=comment.subreddit.display_name
                    )
                except Exception:
                    breakpoint()
                reddit_submission = RedditSubmission.objects.filter(
                    id=comment.submission.id
                ).first()
                if reddit_submission is None:
                    post = client.submission(comment.submission.id)
                    RedditSubmission.make(subreddit=subreddit, post=post)
                    continue
                parent = make_ancestor(comment, reddit_submission)
                RedditComment.make(submission=reddit_submission, comment=comment, parent=parent)
        else:
            logger.warning("Could not get lock, skipping this run")
