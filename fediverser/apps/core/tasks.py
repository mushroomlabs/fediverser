import datetime
import logging
import random

from celery import shared_task
from django.db import transaction
from django.db.models import Max, Q
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from fediverser.apps.lemmy.services import InstanceProxy, LemmyClientRateLimited, LocalUserProxy

from .choices import AutomaticCommentPolicies, AutomaticSubmissionPolicies
from .models.activitypub import Community, Instance, make_ap_client
from .models.common import AP_SERVER_SOFTWARE
from .models.feeds import Entry, Feed
from .models.invites import RedditorInvite
from .models.mapping import InstanceExtraInformation
from .models.mirroring import LemmyMirroredComment, LemmyMirroredPost
from .models.network import FediversedInstance
from .models.reddit import RedditComment, RedditCommunity, RedditSubmission, RejectedPost
from .settings import app_settings

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
        mirror_instance = InstanceProxy.get_connected_instance()
        assert mirror_instance is not None, "no connected Lemmy instance"
        mirror_instance.register(username=reddit_username, as_bot=as_bot)
    except AssertionError as exc:
        logger.info(exc)


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


@shared_task
def send_invite_to_redditor(invite_id):
    try:
        invite = RedditorInvite.objects.get(id=invite_id)
        inviter = invite.inviter

        assert inviter.account.can_send_reddit_private_messages, "can not send DMs"

        reddit = inviter.account.get_reddit_client()

        assert reddit is not None, "Could not get reddit client"

    except RedditorInvite.DoesNotExist:
        logger.warning("Could not find target for invite")
        return
    except AssertionError as exc:
        logger.warning(str(exc))
        return

    subject = f"Invite to join {app_settings.Portal.name}"
    invite_accept_url = reverse(
        "fediverser-core:redditor-accept-invite", kwargs={"key": invite.key}
    )
    invite_decline_url = reverse(
        "fediverser-core:redditor-decline-invite", kwargs={"key": invite.key}
    )

    message = render_to_string(
        "invites/direct_message.tmpl.md",
        context={
            "invite_accept_url": f"{app_settings.Portal.url}{invite_accept_url}",
            "invite_decline_url": f"{app_settings.Portal.url}{invite_decline_url}",
        },
    )

    with transaction.atomic():
        reddit.redditor(invite.redditor.username).message(subject=subject, message=message)
        invite.sent = timezone.now()
        invite.save()


@shared_task
def get_instance_details(domain):
    try:
        instance = Instance.objects.get(domain=domain)
        extra, _ = InstanceExtraInformation.objects.get_or_create(instance=instance)
    except Instance.DoesNotExist:
        logger.warning(f"Instance {domain} not found")
        return

    try:
        if instance.software == AP_SERVER_SOFTWARE.lemmy:
            client = make_ap_client()
            response = client.get(f"{instance.url}/api/v3/site")
            response.raise_for_status()
            data = response.json()
            extra.application_required = (
                data["site_view"]["local_site"]["registration_mode"] == "RequireApplication"
            )
            extra.save()
    except Exception as exc:
        logger.exception("Failed to get instance details", extra={"exception": str(exc)})


@shared_task
def fetch_subreddit(subreddit_name):
    RedditCommunity.fetch(subreddit_name)


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
def push_new_comments_to_lemmy():
    allows_mirroring = Q(
        mirroring_strategies__automatic_comment_policy__in=[
            AutomaticCommentPolicies.FULL,
            AutomaticCommentPolicies.SELF_POST_ONLY,
            AutomaticCommentPolicies.LINK_ONLY,
        ]
    )

    mapped = Q(mirroring_strategies__isnull=False)

    for subreddit in RedditCommunity.objects.filter(mapped & allows_mirroring):
        logger.info(f"Checking comments for {subreddit}")
        mirrored_comments = LemmyMirroredComment.objects.filter(
            lemmy_mirrored_post__reddit_submission__subreddit=subreddit
        )

        most_recent = mirrored_comments.aggregate(most_recent=Max("created")).get("most_recent")
        threshold = most_recent or timezone.now() - datetime.timedelta(minutes=10)

        logger.info(f"Finding all comments created after {threshold}")
        candidates = RedditComment.objects.filter(
            created__gte=threshold,
            submission__subreddit=subreddit,
            status=RedditComment.STATUS.retrieved,
        )

        with_mirrored_submissions = Q(submission__lemmy_mirrored_posts__isnull=False)
        no_pending_parent = Q(parent=None) | Q(parent__status=RedditComment.STATUS.mirrored)

        comments = candidates.filter(with_mirrored_submissions).filter(no_pending_parent)

        for comment in comments.distinct().iterator():
            comment.status = RedditComment.STATUS.accepted
            comment.save()

            logger.info(f"Scheduling mirror of comment {comment.id}")
            mirror_comment_to_lemmy(comment.id)


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

    for reddit_submission in submissions.distinct().order_by("?"):
        logger.info(f"Checking submission {reddit_submission.url}")

        if not reddit_submission.can_be_submitted_automatically:
            reddit_submission.status = RedditSubmission.STATUS.rejected
            reddit_submission.save()
            continue

        community = Community.objects.filter(
            mirroring_strategies__subreddit=reddit_submission.subreddit,
            mirroring_strategies__automatic_submission_policy__in=[
                AutomaticSubmissionPolicies.FULL,
                AutomaticSubmissionPolicies.SELF_POST_ONLY,
                AutomaticSubmissionPolicies.LINK_ONLY,
            ],
        ).first()

        if community is None:
            reddit_submission.status = RedditSubmission.STATUS.rejected
            reddit_submission.save()
            continue

        try:
            LemmyMirroredPost.make_mirror(reddit_submission=reddit_submission, community=community)
            logger.info(f"Posted {reddit_submission.id} to {community.name}")
        except RejectedPost as exc:
            logger.warning(f"Post was rejected: {exc}")
            reddit_submission.status = RedditSubmission.STATUS.rejected
            reddit_submission.save()
        except Exception:
            logger.exception(f"Failed to post {reddit_submission.id}")
            reddit_submission.status = RedditSubmission.STATUS.failed
            reddit_submission.save()


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


@shared_task
def sync_change_feeds():
    # We are going to set this task to run every minute, but to avoid
    # "thundering herd" types of issues, we are going to execute the
    # actual sync call X% of the time, where X is the amount of
    # minutes elapsed since the last sync job.

    # This will mean each instance will have a 50% of being synced
    # after 20 minutes, and 100% after 1h40minutes.

    instances_to_sync = FediversedInstance.partners.all()

    if not instances_to_sync:
        logger.info("No active partners to pull changes from")
    logger.debug(
        f"Attempting sync for {', '.join(instances_to_sync.values_list('portal_url', flat=True))}"
    )

    for instance in instances_to_sync:
        last_sync = instance.sync_jobs.order_by("run_on").first()
        since = last_sync and last_sync.run_on
        if not since:
            instance.sync_change_feeds()
        else:
            minutes_elapsed = int((timezone.now() - since).seconds / 60)

            if (minutes_elapsed / 100) >= random.random():
                instance.sync_change_feeds(since=since)
