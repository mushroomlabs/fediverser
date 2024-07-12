import datetime
import logging
import os
import tempfile

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils import timezone
from model_utils.models import TimeStampedModel
from pythorhead.types import LanguageType

from fediverser.apps.lemmy.models import Post
from fediverser.apps.lemmy.services import (
    InstanceProxy,
    LemmyClientRateLimited,
    LemmyProxyUserNotConfigured,
    LocalUserProxy,
)

from ..choices import AutomaticCommentPolicies, AutomaticSubmissionPolicies
from .activitypub import Community
from .reddit import RedditComment, RedditCommunity, RedditSubmission, RejectedComment, RejectedPost

logger = logging.getLogger(__name__)
User = get_user_model()


class RedditMirrorStrategy(models.Model):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="mirroring_strategies", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="mirroring_strategies", on_delete=models.CASCADE
    )

    automatic_submission_policy = models.TextField(
        max_length=16,
        choices=AutomaticSubmissionPolicies.choices,
        default=AutomaticSubmissionPolicies.NONE,
    )
    automatic_comment_policy = models.TextField(
        max_length=16,
        choices=AutomaticCommentPolicies.choices,
        default=AutomaticCommentPolicies.NONE,
    )
    automatic_submission_limit = models.SmallIntegerField(
        null=True, blank=True, help_text="Limit of maximum automatic submissions per 24h"
    )

    @property
    def accepts_automatic_submissions(self):
        return self.automatic_submission_policy != AutomaticSubmissionPolicies.NONE

    @property
    def accepts_self_posts(self):
        return self.automatic_submission_policy in [
            AutomaticSubmissionPolicies.SELF_POST_ONLY,
            AutomaticSubmissionPolicies.FULL,
        ]

    @property
    def accepts_link_posts(self):
        return self.automatic_submission_policy in [
            AutomaticSubmissionPolicies.LINK_ONLY,
            AutomaticSubmissionPolicies.FULL,
        ]

    def can_submit_to_lemmy(self, reddit_submission, community):
        # Reject because community does not want automatic submissions
        if not self.accepts_automatic_submissions:
            return False

        # Community does not want self posts
        if reddit_submission.is_self_post and not self.accepts_self_posts:
            return False

        # Community does not want link posts
        if reddit_submission.is_link_post and not self.accepts_link_posts:
            return False

        duplicates = Post.objects.filter(url=reddit_submission.url)

        # Community already has this url posted
        if (
            community.mirroring is not None
            and duplicates.filter(community=community.mirroring).exists()
        ):
            return False

        # Community does not want to be flooded with automatic submissions
        now = timezone.now()
        one_day_ago = now - datetime.timedelta(days=1)
        recent_mirrored_posts = LemmyMirroredPost.objects.filter(
            community=community, created__gte=one_day_ago
        )
        if self.automatic_submission_limit is not None:
            if recent_mirrored_posts.count() >= self.automatic_submission_limit:
                return False

        # Community has no objection to this submission
        return True

    class Meta:
        unique_together = ("subreddit", "community")
        verbose_name_plural = "Reddit Mirror Strategies"


class LemmyMirroredPost(TimeStampedModel):
    reddit_submission = models.ForeignKey(
        RedditSubmission, null=True, related_name="lemmy_mirrored_posts", on_delete=models.SET_NULL
    )
    lemmy_post_id = models.PositiveIntegerField(db_index=True)
    community = models.ForeignKey(
        Community, related_name="reddit_crossposts", on_delete=models.CASCADE
    )

    def submit_disclosure_comment(self):
        try:
            lemmy_mirror = InstanceProxy.get_connected_instance()
            fediverser_bot = LocalUserProxy.get_fediverser_bot()
            client = fediverser_bot.make_lemmy_client()
            logger.info(
                f"Submitting disclosure comment for reddit post {self.reddit_submission.id}"
            )

            body = render_to_string(
                "fediverser/messages/mirrored_post_disclosure.tmpl.md",
                {
                    "mirrored_post": self,
                    "mirror_instance": lemmy_mirror,
                    "portal_url": settings.PORTAL_URL,
                },
            )
            params = dict(post_id=self.lemmy_post_id, content=body)

            client.comment.create(**params)

        except LemmyProxyUserNotConfigured:
            logger.warning("Missing configuration for proxy user")

    @classmethod
    def make_mirror(cls, reddit_submission, community, lemmy_user=None):
        mirrored_post = cls.objects.filter(
            reddit_submission=reddit_submission, community=community
        ).first()

        if mirrored_post is None:
            reddit_submission.validate()

            logger.info(f"Syncing reddit post {reddit_submission.id} to {community.name}")
            if lemmy_user is None:
                lemmy_user = LocalUserProxy.get_mirror_user(reddit_submission.author.username)
            lemmy_client = lemmy_user.make_lemmy_client()

            post_language = (
                reddit_submission.language
                if reddit_submission.language in community.languages
                else LanguageType.UNDETERMINED
            )

            payload = reddit_submission.to_lemmy_post_payload()

            payload.update(
                {
                    "community_id": lemmy_client.discover_community(community.fqdn),
                    "language_id": post_language.value,
                }
            )

            if reddit_submission.is_image_hosted_on_reddit:
                _, suffix = reddit_submission.url.rsplit(".", 1)

                file_name = ".".join([slugify(reddit_submission.title), suffix])

                image_download = requests.get(reddit_submission.url)
                image_download.raise_for_status()
                with tempfile.TemporaryDirectory() as td:
                    file_path = os.path.join(td, file_name)
                    with open(file_path, "w+b") as f:
                        f.write(image_download.content)
                    upload_response = lemmy_client.image.upload(file_path)
                try:
                    payload["url"] = upload_response[0]["image_url"]
                except (TypeError, AttributeError, KeyError):
                    raise RejectedPost("Image could not be uploaded")

            with transaction.atomic():
                try:
                    lemmy_post = lemmy_client.post.create(**payload)
                    mirrored_post = cls.objects.create(
                        reddit_submission=reddit_submission,
                        lemmy_post_id=lemmy_post["post_view"]["post"]["id"],
                        community=community,
                    )
                    reddit_submission.status = reddit_submission.STATUS.mirrored
                except Exception as exc:
                    if "rate_limit_error" in str(exc):
                        raise LemmyClientRateLimited()
                    else:
                        reddit_submission.status = reddit_submission.STATUS.failed
                        logger.info(f"Failed to post {reddit_submission.id}: {exc}")
                reddit_submission.save()

        return mirrored_post

    class Meta:
        unique_together = (
            ("reddit_submission", "lemmy_post_id"),
            ("reddit_submission", "community"),
        )


class LemmyMirroredComment(TimeStampedModel):
    lemmy_mirrored_post = models.ForeignKey(
        LemmyMirroredPost, related_name="comments", on_delete=models.CASCADE
    )
    lemmy_comment_id = models.PositiveIntegerField(db_index=True)
    reddit_comment = models.ForeignKey(
        RedditComment, null=True, related_name="lemmy_mirrored_comments", on_delete=models.SET_NULL
    )

    @classmethod
    def make_mirror(cls, reddit_comment, mirrored_post, include_children=True):
        if reddit_comment.status == RedditComment.STATUS.mirrored:
            logger.info(f"Comment {reddit_comment.id} is already mirrored")
            return

        try:
            reddit_comment.validate()
        except RejectedComment:
            reddit_comment.status = RedditComment.STATUS.rejected
            reddit_comment.save()
            return

        mirrored_comment = cls.objects.filter(
            reddit_comment=reddit_comment, lemmy_mirrored_post=mirrored_post
        ).first()

        if mirrored_comment is None:
            logger.debug(f"Posting reddit comment {reddit_comment.id} to lemmy mirrors")
            lemmy_user = LocalUserProxy.get_mirror_user(reddit_comment.author.username)
            lemmy_client = lemmy_user.make_lemmy_client()
            post_language = reddit_comment.language
            if reddit_comment.language not in mirrored_post.community.languages:
                post_language = LanguageType.UNDETERMINED

            lemmy_parent = (
                reddit_comment.parent
                and mirrored_post.comments.filter(reddit_comment=reddit_comment.parent).first()
            )

            params = dict(
                post_id=mirrored_post.lemmy_post_id,
                content=reddit_comment.body,
                language_id=post_language.value,
                parent_id=lemmy_parent and lemmy_parent.lemmy_comment_id,
            )

            with transaction.atomic():
                try:
                    lemmy_comment = lemmy_client.comment.create(**params)
                except Exception as exc:
                    if "rate_limit_error" in str(exc):
                        raise LemmyClientRateLimited()

                    lemmy_comment = None
                    reddit_comment.status = RedditComment.STATUS.failed
                    logger.info(f"Failed to post {reddit_comment.id}: {exc}")
                else:
                    new_comment_id = lemmy_comment["comment_view"]["comment"]["id"]

                    mirrored_comment = LemmyMirroredComment.objects.create(
                        lemmy_mirrored_post=mirrored_post,
                        reddit_comment=reddit_comment,
                        lemmy_comment_id=new_comment_id,
                    )
                    reddit_comment.status = RedditComment.STATUS.mirrored
                    logger.debug(f"Posted comment {new_comment_id} ({mirrored_post.community})")
                reddit_comment.save()

        if include_children:
            for reply in reddit_comment.children.all():
                cls.make_mirror(reply, mirrored_post, include_children=True)

        return mirrored_comment

    class Meta:
        unique_together = ("lemmy_mirrored_post", "lemmy_comment_id")


all = ("RedditMirrorStrategy", "LemmyMirroredPost", "LemmyMirroredComment")
