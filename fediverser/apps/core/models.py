import datetime
import logging
import os
import secrets
import tempfile
from typing import Optional

import bcrypt
import praw
import requests
from Crypto.PublicKey import RSA
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.db.models import Max
from django.db.utils import DataError
from django.template.defaultfilters import slugify
from django.utils import timezone
from django.utils.timezone import make_aware
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from model_utils.models import StatusModel, TimeStampedModel
from praw import Reddit
from pythorhead.types import LanguageType

from fediverser.apps.lemmy import models as lemmy_models

from .choices import SOURCE_CONTENT_STATUSES, AutomaticCommentPolicies, AutomaticSubmissionPolicies
from .exceptions import LemmyClientRateLimited, RejectedComment, RejectedPost

logger = logging.getLogger(__name__)


LEMMY_CLIENTS = {}
User = get_user_model()


def make_reddit_client(**kw):
    return Reddit(
        client_id=settings.REDDIT_CLIENT_ID,
        client_secret=settings.REDDIT_CLIENT_SECRET,
        user_agent=settings.REDDIT_USER_AGENT,
        **kw,
    )


def make_reddit_user_client(social_application, refresh_token):
    return Reddit(
        client_id=social_application.client_id,
        client_secret=social_application.secret,
        user_agent=settings.REDDIT_USER_AGENT,
        refresh_token=refresh_token,
    )


def make_password():
    return secrets.token_urlsafe(30)


def generate_rsa_keypair(keysize: int = 2048):
    key = RSA.generate(keysize)
    public_key_pem = key.publickey().export_key().decode()
    private_key_pem = key.export_key().decode()

    return (private_key_pem, public_key_pem)


def get_hashed_password(cleartext: str) -> str:
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(cleartext.encode(), salt=salt)
    return hashed_bytes.decode()


class LemmyInstance(models.Model):
    domain = models.CharField(max_length=255, unique=True)

    @property
    def mirroring(self):
        return lemmy_models.Instance.objects.filter(domain=self.domain).first()

    def __str__(self):
        return self.domain


class LemmyCommunity(models.Model):
    instance = models.ForeignKey(
        LemmyInstance, related_name="communities", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)

    @property
    def fqdn(self):
        return f"{self.name}@{self.instance.domain}"

    @property
    def url(self):
        return f"https://{self.instance.domain}/c/{self.name}"

    @property
    def languages(self):
        return [
            LanguageType(language_id)
            for language_id in (
                lemmy_models.Language.objects.filter(
                    communitylanguage__community__name=self.name,
                    communitylanguage__community__instance__domain=self.instance.domain,
                ).values_list("id", flat=True)
            )
        ]

    @property
    def mirroring(self):
        if self.instance.mirroring is None:
            return None

        return lemmy_models.Community.objects.filter(
            instance=self.instance.mirroring, name=self.name
        ).first()

    def can_accept_automatic_submission(self, reddit_submission):
        try:
            lemmy_poster = RedditToLemmyCommunity.objects.get(
                subreddit=reddit_submission.subreddit, lemmy_community=self
            )

            # Reject because community does not want automatic submissions
            if not lemmy_poster.accepts_automatic_submissions:
                return False

            # Community does not want self posts
            if reddit_submission.is_self_post and not lemmy_poster.accepts_self_posts:
                return False

            # Community does not want link posts
            if reddit_submission.is_link_post and not lemmy_poster.accepts_link_posts:
                return False

            duplicates = lemmy_models.Post.objects.filter(url=reddit_submission.url)

            # Community already has this url posted
            if self.mirroring is not None and duplicates.filter(community=self.mirroring).exists():
                return False

            # Community does not want to be flooded with automatic submissions
            now = timezone.now()
            one_day_ago = now - datetime.timedelta(days=1)
            recent_mirrored_posts = LemmyMirroredPost.objects.filter(
                lemmy_community=self, created__gte=one_day_ago
            )
            if lemmy_poster.automatic_submission_limit is not None:
                if recent_mirrored_posts.count() >= lemmy_poster.automatic_submission_limit:
                    return False

            # Community has no objection to this submission
            return True

        except RedditToLemmyCommunity.DoesNotExist:
            return False

    def __str__(self):
        return self.fqdn

    class Meta:
        unique_together = ("instance", "name")
        verbose_name_plural = "Lemmy Communities"


class RedditCommunity(models.Model):
    name = models.CharField(max_length=255, unique=True)
    last_synced_at = models.DateTimeField(null=True)

    @property
    def comments(self):
        return RedditComment.objects.filter(submission__subreddit=self)

    @property
    def most_recent_post(self):
        return self.posts.aggregate(most_recent=Max("created")).get("most_recent")

    @property
    def most_recent_comment(self):
        return self.comments.aggregate(most_recent=Max("created")).get("most_recent")

    @property
    def praw_object(self):
        reddit = make_reddit_client()
        return reddit.subreddit(self.name)

    def __str__(self):
        return f"/r/{self.name}"

    class Meta:
        verbose_name_plural = "Subreddit"
        verbose_name_plural = "Subreddits"


class RedditAccount(models.Model):
    controller = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    username = models.CharField(unique=True, max_length=60)
    password = models.CharField(
        max_length=64, default=make_password, help_text="Password for Lemmy mirror instance"
    )
    rejected_invite = models.BooleanField(default=False)
    marked_as_spammer = models.BooleanField(default=False)
    marked_as_bot = models.BooleanField(default=False)
    subreddits = models.ManyToManyField(RedditCommunity, blank=True)

    @property
    def is_initial_password_in_use(self):
        lemmy_mirror = lemmy_models.Instance.get_reddit_mirror()
        if lemmy_mirror is None:
            logger.warning("Lemmy Mirror instance is not properly configured")
            return False

        try:
            lemmy_user = lemmy_models.LocalUser.objects.get(person__name=self.username)
            return bcrypt.checkpw(self.password.encode(), lemmy_user.password_encrypted.encode())
        except lemmy_models.LocalUser.DoesNotExist:
            logger.warning(f"Lemmy Mirror does not have user {self.username}")
            return False

    @property
    def can_send_invite(self):
        now = timezone.now()
        return all(
            [
                self.controller is None,
                not self.rejected_invite,
                not self.marked_as_spammer,
                not self.invites.filter(created__gte=now - datetime.timedelta(days=7)).exists(),
            ]
        )

    def unbot_mirror(self):
        lemmy_mirror = lemmy_models.Instance.get_reddit_mirror()
        if lemmy_mirror is None:
            logger.warning("Lemmy Mirror instance is not properly configured")
            return

        lemmy_models.Person.objects.filter(name=self.username, instance=lemmy_mirror).update(
            bot_account=False
        )

    def register_mirror(self, as_bot=True):
        lemmy_mirror = lemmy_models.Instance.get_reddit_mirror()
        if lemmy_mirror is None:
            logger.warning("Lemmy Mirror instance is not properly configured")
            return

        private_key, public_key = generate_rsa_keypair()

        person, _ = lemmy_models.Person.objects.get_or_create(
            name=self.username,
            instance=lemmy_mirror,
            defaults={
                "actor_id": f"https://{lemmy_mirror.domain}/u/{self.username}",
                "inbox_url": f"https://{lemmy_mirror.domain}/u/{self.username}/inbox",
                "shared_inbox_url": f"https://{lemmy_mirror.domain}/inbox",
                "private_key": private_key,
                "public_key": public_key,
                "published": timezone.now(),
                "last_refreshed_at": timezone.now(),
                "local": True,
                "bot_account": as_bot,
                "deleted": False,
                "banned": False,
                "admin": False,
            },
        )
        local_user, _ = lemmy_models.LocalUser.objects.update_or_create(
            person=person,
            defaults={
                "password_encrypted": get_hashed_password(self.password),
                "accepted_application": True,
            },
        )

    @property
    def mirror_lemmy_user(self):
        return lemmy_models.LocalUser.objects.get(person__name=self.username)

    def make_lemmy_client(self):
        global LEMMY_CLIENTS

        if self.username in LEMMY_CLIENTS:
            return LEMMY_CLIENTS[self.username]

        lemmy_mirror = lemmy_models.Instance.get_reddit_mirror()

        lemmy_client = lemmy_mirror._get_client()
        lemmy_client.log_in(self.username, self.password)
        LEMMY_CLIENTS[self.username] = lemmy_client

        return lemmy_client

    @classmethod
    def make(cls, redditor: praw.models.Redditor):
        if redditor is None:
            return None

        account, _ = cls.objects.get_or_create(username=redditor.name)
        return account

    def __str__(self):
        return f"/u/{self.username}"


class AbstractRedditItem(TimeStampedModel, StatusModel):
    STATUS = SOURCE_CONTENT_STATUSES
    id = models.CharField(max_length=16, primary_key=True)

    @property
    def language_code(self):
        raise NotImplementedError()

    @property
    def language(self):
        try:
            return self.language_code and LanguageType[self.language_code.upper()]
        except (KeyError, AttributeError, LangDetectException):
            return LanguageType.UNDETERMINED

    class Meta:
        abstract = True


class RedditSubmission(AbstractRedditItem):
    subreddit = models.ForeignKey(RedditCommunity, related_name="posts", on_delete=models.CASCADE)
    author = models.ForeignKey(
        RedditAccount, null=True, related_name="posts", on_delete=models.SET_NULL
    )
    url = models.URLField(db_index=True)
    title = models.TextField()
    selftext = models.TextField(null=True, blank=True)
    selftext_html = models.TextField(null=True, blank=True)
    media_only = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True)
    banned_at = models.DateTimeField(null=True)
    archived = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)
    quarantined = models.BooleanField(default=False)
    removed = models.BooleanField(default=False)
    over_18 = models.BooleanField(default=False)
    marked_as_spam = models.BooleanField(default=False)
    marked_as_duplicate = models.BooleanField(default=False)

    @property
    def has_self_text(self):
        return self.selftext is not None and self.selftext.strip()

    @property
    def is_link_post(self):
        return not any(
            [
                self.is_cross_post,
                self.is_media_hosted_on_reddit,
                self.url.startswith("https://reddit.com"),
            ]
        )

    @property
    def is_self_post(self):
        return self.url.startswith("https://reddit.com") or self.has_self_text

    @property
    def is_cross_post(self):
        return self.url.startswith("/r/")

    @property
    def can_be_submitted_automatically(self):
        return all(
            [
                not self.over_18,
                not self.banned_at,
                not self.quarantined,
                not self.removed,
                not self.is_cross_post,
                self.url is not None and not self.url.startswith("https://twitter.com"),
                self.url is not None and not self.url.startswith("https://x.com"),
                not self.is_video_hosted_on_reddit,
                not self.is_gallery_hosted_on_reddit,
                not self.marked_as_spam,
                not self.marked_as_duplicate,
                self.author is not None and not self.author.marked_as_bot,
                self.author is not None and not self.author.marked_as_spammer,
            ]
        )

    @property
    def banned(self):
        return self.banned_at is not None

    @property
    def is_gallery_hosted_on_reddit(self):
        return self.url.startswith("https://www.reddit.com/gallery/")

    @property
    def is_image_hosted_on_reddit(self):
        return self.url.startswith("https://i.redd.it")

    @property
    def is_video_hosted_on_reddit(self):
        return self.url.startswith("https://v.redd.it")

    @property
    def is_media_hosted_on_reddit(self):
        return self.is_image_hosted_on_reddit or self.is_video_hosted_on_reddit

    @property
    def language_code(self):
        text = self.title if not self.is_self_post else f"{self.title}\n {self.selftext}"
        return detect(text)

    @property
    def praw_object(self):
        reddit = make_reddit_client()
        return reddit.submission(id=self.id)

    def validate(self):
        try:
            assert len(self.title) > 3, "Post title is too short"
            assert len(self.title) < 200, "Post title is too long"
            assert not self.removed, "Post has been removed on reddit"
            assert self.selftext != "[removed]", "Post content was removed on reddit"
        except AssertionError as exc:
            raise RejectedPost(str(exc))

    def to_lemmy_post_payload(self):
        MAX_TITLE_LENGTH = 200

        post_title = self.title[:MAX_TITLE_LENGTH]

        payload = dict(
            name=post_title,
            nsfw=self.over_18,
        )

        if self.is_link_post:
            payload["url"] = self.url

        if self.has_self_text:
            payload["body"] = self.selftext

        return payload

    def post_to_lemmy(self, lemmy_community):
        mirrored_post = LemmyMirroredPost.objects.filter(
            reddit_submission=self, lemmy_community=lemmy_community
        ).first()

        if mirrored_post is None:
            self.validate()

            logger.info(f"Syncing reddit post {self.id} to {lemmy_community.name}")
            lemmy_client = self.author.make_lemmy_client()

            post_language = (
                self.language
                if self.language in lemmy_community.languages
                else LanguageType.UNDETERMINED
            )

            payload = self.to_lemmy_post_payload()

            payload.update(
                {
                    "community_id": lemmy_client.discover_community(lemmy_community.fqdn),
                    "language_id": post_language.value,
                }
            )

            if self.is_image_hosted_on_reddit:
                _, suffix = self.url.rsplit(".", 1)

                file_name = ".".join([slugify(self.title), suffix])

                image_download = requests.get(self.url)
                image_download.raise_for_status()
                with tempfile.TemporaryDirectory() as td:
                    file_path = os.path.join(td, file_name)
                    with open(file_path, "w+b") as f:
                        f.write(image_download.content)
                    upload_response = lemmy_client.image.upload(file_path)
                payload["url"] = upload_response[0]["image_url"]

            with transaction.atomic():
                try:
                    lemmy_post = lemmy_client.post.create(**payload)
                    mirrored_post = LemmyMirroredPost.objects.create(
                        reddit_submission=self,
                        lemmy_post_id=lemmy_post["post_view"]["post"]["id"],
                        lemmy_community=lemmy_community,
                    )
                    self.status = self.STATUS.mirrored
                except Exception as exc:
                    if "rate_limit_error" in str(exc):
                        raise LemmyClientRateLimited()
                    else:
                        self.status = self.STATUS.failed
                        logger.info(f"Failed to post {self.id}: {exc}")
                self.save()

        return mirrored_post

    @classmethod
    def make(cls, subreddit: RedditCommunity, post: praw.models.Submission):
        def get_date(timestamp):
            return timestamp and make_aware(datetime.datetime.fromtimestamp(timestamp))

        def make_comment_thread(submission, comment: praw.models.Comment, parent=None):
            reddit_comment = RedditComment.make(
                submission=submission, comment=comment, parent=parent
            )
            for reply in comment.replies:
                make_comment_thread(submission=submission, comment=reply, parent=reddit_comment)

        logger.info(f"Syncing reddit post {post.id}")

        author = RedditAccount.make(post.author)
        try:
            submission, _ = subreddit.posts.update_or_create(
                id=post.id,
                defaults=dict(
                    author=author,
                    url=post.url,
                    title=post.title,
                    created=get_date(post.created_utc),
                    selftext=post.selftext,
                    selftext_html=post.selftext_html,
                    media_only=post.media_only,
                    approved_at=get_date(post.approved_at_utc),
                    banned_at=get_date(post.banned_at_utc),
                    archived=post.archived,
                    locked=post.locked,
                    quarantined=post.quarantine,
                    removed=post.removed_by is not None,
                    over_18=post.over_18,
                ),
            )

            # Remove all "more comments" from the tree of comments. Reasons:
            # - Avoid extra requests on posts with hellthreads.
            # - We don't really care about hellthreads
            # - Most posts with lots of comments are usually "daily discussion", not to repost.
            # - If we are pulling in (near) real-time, there will be few comments anyway
            # - When we get a "new" comment deep in the tree, it builds the whole ancestry anyway.

            post.comments.replace_more(limit=0)
            for comment in post.comments:
                make_comment_thread(submission=submission, comment=comment, parent=None)
            return submission
        except DataError:
            logger.warning("Failed to make reddit submission", extra={"post_url": post.url})

    def __str__(self):
        return f"{self.url} ({self.subreddit})"


class RedditComment(AbstractRedditItem):
    MAXIMUM_AGE_FOR_MIRRORING = datetime.timedelta(days=1)
    submission = models.ForeignKey(
        RedditSubmission, related_name="comments", on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        RedditAccount, null=True, related_name="comments", on_delete=models.SET_NULL
    )
    parent = models.ForeignKey(
        "RedditComment", related_name="children", null=True, on_delete=models.SET_NULL
    )
    permalink = models.URLField(db_index=True)
    body = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    stickied = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    distinguished = models.BooleanField(default=False)
    marked_as_spam = models.BooleanField(default=False)

    @property
    def is_submitter(self):
        return self.author_id == self.submission.author_id

    @property
    def language_code(self):
        return self.body and detect(self.body)

    @property
    def age(self):
        return timezone.now() - self.created

    def make_mirror(self, mirrored_post, include_children=True):
        try:
            no_missing_parent = self.parent is None or self.parent.status == self.STATUS.mirrored
            assert no_missing_parent, "Parent comment is not mirrored"
            assert self.age <= self.MAXIMUM_AGE_FOR_MIRRORING, "Comment is too old"
            assert not self.marked_as_spam, "Comment is marked as spam"
            assert not self.stickied, "Sticked comments only make sense for reddit"
            assert self.author is not None, "Author is unknown"
            assert not self.author.marked_as_bot, "Author is marked as bot"
            assert not self.author.marked_as_spammer, "Author is marked as spammer"
            assert not self.submission.marked_as_spam, "Submission has been marked as spam"
        except AssertionError as exc:
            self.status = self.STATUS.rejected
            self.save()
            raise RejectedComment(str(exc))

        mirrored_comment = self.lemmy_mirrored_comments.filter(
            lemmy_mirrored_post=mirrored_post
        ).first()

        if mirrored_comment is None:
            logger.debug(f"Posting reddit comment {self.id} to lemmy mirrors")
            lemmy_client = self.author.make_lemmy_client()
            post_language = self.language
            if self.language not in mirrored_post.lemmy_community.languages:
                post_language = LanguageType.UNDETERMINED

            lemmy_parent = (
                self.parent and mirrored_post.comments.filter(reddit_comment=self.parent).first()
            )

            params = dict(
                post_id=mirrored_post.lemmy_post_id,
                content=self.body,
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
                    self.status = self.STATUS.failed
                    logger.info(f"Failed to post {self.id}: {exc}")
                else:
                    new_comment_id = lemmy_comment["comment_view"]["comment"]["id"]

                    mirrored_comment = LemmyMirroredComment.objects.create(
                        lemmy_mirrored_post=mirrored_post,
                        reddit_comment=self,
                        lemmy_comment_id=new_comment_id,
                    )
                    self.status = self.STATUS.mirrored
                    logger.debug(
                        f"Posted comment {new_comment_id} ({mirrored_post.lemmy_community})"
                    )
                self.save()

        if include_children:
            for reply in self.children.all():
                reply.make_mirror(mirrored_post, include_children=True)

        return mirrored_comment

    def __str__(self):
        return self.permalink

    @classmethod
    def make(
        cls,
        submission: RedditSubmission,
        comment: praw.models.Comment,
        parent: Optional["RedditComment"] = None,
    ):
        logger.info(f"Syncing reddit comment {comment.id}")
        commenter = RedditAccount.make(comment.author)
        reddit_comment, _ = cls.objects.update_or_create(
            id=comment.id,
            defaults={
                "submission": submission,
                "author": commenter,
                "parent": parent,
                "permalink": comment.permalink,
                "body": comment.body,
                "body_html": comment.body_html,
                "stickied": bool(comment.stickied),
                "edited": bool(comment.edited),
                "distinguished": bool(comment.distinguished),
                "created": make_aware(datetime.datetime.fromtimestamp(comment.created_utc)),
            },
        )
        return reddit_comment


class RedditToLemmyCommunity(models.Model):
    subreddit = models.ForeignKey(RedditCommunity, on_delete=models.CASCADE)
    lemmy_community = models.ForeignKey(LemmyCommunity, on_delete=models.CASCADE)

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

    class Meta:
        unique_together = ("subreddit", "lemmy_community")
        verbose_name_plural = "Reddit to Lemmy Community Map"


class LemmyMirroredPost(TimeStampedModel):
    reddit_submission = models.ForeignKey(
        RedditSubmission, null=True, related_name="lemmy_mirrored_posts", on_delete=models.SET_NULL
    )
    lemmy_post_id = models.PositiveIntegerField(db_index=True)
    lemmy_community = models.ForeignKey(
        LemmyCommunity, related_name="reddit_crossposts", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = (
            ("reddit_submission", "lemmy_post_id"),
            ("reddit_submission", "lemmy_community"),
        )


class LemmyMirroredComment(TimeStampedModel):
    lemmy_mirrored_post = models.ForeignKey(
        LemmyMirroredPost, related_name="comments", on_delete=models.CASCADE
    )
    lemmy_comment_id = models.PositiveIntegerField(db_index=True)
    reddit_comment = models.ForeignKey(
        RedditComment, null=True, related_name="lemmy_mirrored_comments", on_delete=models.SET_NULL
    )

    class Meta:
        unique_together = ("lemmy_mirrored_post", "lemmy_comment_id")


class LemmyCommunityInviteTemplate(models.Model):
    """
    A template text for sending automated invites to a given community
    """

    subreddit = models.ForeignKey(
        RedditCommunity, related_name="invite_templates", on_delete=models.CASCADE
    )
    lemmy_community = models.ForeignKey(
        LemmyCommunity, related_name="invite_templates", on_delete=models.CASCADE
    )
    message = models.TextField()

    class Meta:
        unique_together = ("subreddit", "lemmy_community")


class LemmyCommunityInvite(TimeStampedModel):
    """
    A record to indicate when a message inviting a redditor has been sent
    """

    redditor = models.ForeignKey(RedditAccount, related_name="invites", on_delete=models.CASCADE)
    template = models.ForeignKey(
        LemmyCommunityInviteTemplate,
        related_name="invites_sent",
        null=True,
        on_delete=models.SET_NULL,
    )
