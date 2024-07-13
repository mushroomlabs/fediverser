import datetime
import logging
import os
import secrets
import tempfile
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
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

    @staticmethod
    def reddit_to_lemmy_post(reddit_submission):
        MAX_TITLE_LENGTH = 200

        post_title = reddit_submission.title[:MAX_TITLE_LENGTH]

        payload = dict(
            name=post_title,
            nsfw=reddit_submission.over_18,
        )

        if reddit_submission.is_link_post:
            payload["url"] = reddit_submission.url

        if reddit_submission.has_self_text:
            payload["body"] = reddit_submission.selftext

        return payload

    @staticmethod
    def lemmy_post_payload_to_query_string(post_payload):
        query_string = {
            "url": post_payload.get("url"),
            "title": post_payload.get("name"),
            "body": post_payload.get("body"),
            "languageId": post_payload.get("language_id"),
            "communityId": post_payload.get("community_id"),
        }

        return urlencode({k: v for k, v in query_string.items() if v is not None})

    @staticmethod
    def mirror_media(lemmy_client, media_url):
        _, suffix = media_url.rsplit(".", 1)

        file_name = f"{secrets.token_urlsafe(30)}.{suffix}"

        try:
            download = requests.get(media_url)
            download.raise_for_status()
            with tempfile.TemporaryDirectory() as td:
                file_path = os.path.join(td, file_name)
                with open(file_path, "w+b") as f:
                    f.write(download.content)
                upload_response = lemmy_client.image.upload(file_path)
            return upload_response[0]["image_url"]
        except (TypeError, AttributeError, KeyError):
            return None

    @classmethod
    def prepare_lemmy_post_from_reddit_submission(
        cls, lemmy_client, reddit_submission, community: Community
    ):
        payload = LemmyMirroredPost.reddit_to_lemmy_post(reddit_submission)

        post_language = (
            reddit_submission.language
            if reddit_submission.language in community.languages
            else LanguageType.UNDETERMINED
        )

        payload.update(
            {
                "language_id": post_language.value,
                "community_id": lemmy_client.discover_community(community.fqdn),
            }
        )

        if reddit_submission.is_gallery_hosted_on_reddit:
            gallery = []

            for media_item in reddit_submission.praw_object.media_metadata.items():
                media_url = media_item[1]["p"][0]["u"]
                media_url = media_url.split("?", 1)[0]
                media_url = media_url.replace("preview", "i")
                mirrored_url = LemmyMirroredPost.mirror_media(lemmy_client, media_url)
                if mirrored_url is not None:
                    gallery.append(mirrored_url)
            head, *rest = gallery

            if not head:
                raise RejectedPost("Could not get any image from gallery")

            payload["url"] = head
            payload["body"] = "\n\n".join(["![](url)" for url in rest])
            return payload

        if reddit_submission.is_image_hosted_on_reddit:
            try:
                image_url = LemmyMirroredPost.mirror_media(lemmy_client, reddit_submission.url)
                assert image_url is not None, "Image could not be uploaded"
                payload["url"] = image_url
            except AssertionError as exc:
                raise RejectedPost({exc})

        if reddit_submission.is_link_post:
            payload["url"] = reddit_submission.url

        if reddit_submission.has_self_text:
            payload["body"] = reddit_submission.selftext

        return payload

    @classmethod
    def make_mirror(cls, reddit_submission, community, lemmy_user=None):
        mirrored_post = cls.objects.filter(
            reddit_submission=reddit_submission, community=community
        ).first()

        if mirrored_post is None:
            logger.info(f"Syncing reddit post {reddit_submission.id} to {community.name}")
            if lemmy_user is None:
                lemmy_user = LocalUserProxy.get_mirror_user(reddit_submission.author.username)
            lemmy_client = lemmy_user.make_lemmy_client()

            with transaction.atomic():
                try:
                    reddit_submission.validate()
                    payload = cls.prepare_lemmy_post_from_reddit_submission(
                        lemmy_client, reddit_submission, community
                    )

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
