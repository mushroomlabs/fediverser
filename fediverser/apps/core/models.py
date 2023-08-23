import datetime
import logging
import secrets
from typing import Optional

import praw
from django.conf import settings
from django.db import models
from django.db.models import Max
from django.db.utils import DataError
from django.utils.timezone import make_aware
from langdetect import detect
from model_utils.models import TimeStampedModel
from praw import Reddit
from pythorhead import Lemmy

logger = logging.getLogger(__name__)


def make_password():
    return secrets.token_urlsafe(30)


class LemmyInstance(models.Model):
    domain = models.CharField(max_length=255, unique=True)

    @staticmethod
    def get_reddit_mirror():
        return LemmyInstance.objects.get(domain=settings.LEMMY_MIRROR_INSTANCE_DOMAIN)

    def _get_client(self):
        return Lemmy(f"https://{self.domain}")

    def __str__(self):
        return self.domain


class LemmyCommunity(models.Model):
    instance = models.ForeignKey(
        LemmyInstance, related_name="communities", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)

    @property
    def fqdn(self):
        return f"!{self.name}@{self.instance.domain}"

    def __str__(self):
        return self.fqdn

    class Meta:
        unique_together = ("instance", "name")
        verbose_name_plural = "Lemmy Communities"


class RedditCommunity(models.Model):
    name = models.CharField(max_length=255, unique=True)

    @property
    def most_recent_post(self):
        return self.posts.aggregate(most_recent=Max("created")).get("most_recent")

    def __str__(self):
        return f"/r/{self.name}"

    def _get_client(self):
        reddit = Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )
        return reddit.subreddit(self.name)

    def new(self):
        return self._get_client().new()

    class Meta:
        verbose_name_plural = "Subreddit"
        verbose_name_plural = "Subreddits"


class RedditAccount(models.Model):
    username = models.CharField(unique=True, max_length=60)
    password = models.CharField(
        max_length=64, default=make_password, help_text="Password for Lemmy mirror instance"
    )

    @classmethod
    def make(cls, redditor: praw.models.Redditor):
        if redditor is None:
            return None

        account, _ = cls.objects.get_or_create(username=redditor.name)
        return account

    def __str__(self):
        return f"/u/{self.username}"


class RedditSubmission(TimeStampedModel):
    id = models.CharField(max_length=16, primary_key=True)
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

    @property
    def is_self_post(self):
        return self.url.startswith("https://reddit.com")

    @property
    def language_code(self):
        text = self.title if not self.is_self_post else f"{self.title}\n {self.selftext}"
        return detect(text)

    @classmethod
    def make(cls, subreddit: RedditCommunity, post: praw.models.Submission):
        def get_date(timestamp):
            return timestamp and make_aware(datetime.datetime.fromtimestamp(timestamp))

        author = RedditAccount.make(post.author)
        try:
            submission = subreddit.posts.create(
                id=post.id,
                author=author,
                url=post.url,
                title=post.title,
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
            )
            for comment in post.comments:
                RedditComment.make(submission=submission, comment=comment)
        except DataError:
            logger.warning("Failed to make reddit submission", extra={"post_url": post.url})

    def __str__(self):
        return f"{self.url} ({self.subreddit})"


class RedditComment(TimeStampedModel):
    id = models.CharField(max_length=16, primary_key=True)
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

    @property
    def is_submitter(self):
        return self.author_id == self.submission.author_id

    @property
    def language_code(self):
        return self.body and detect(self.body)

    def __str__(self):
        return self.permalink

    @classmethod
    def make(
        cls,
        submission: RedditSubmission,
        comment: praw.models.Comment,
        parent: Optional["RedditComment"] = None,
    ):
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
        for reply in comment.replies:
            cls.make(submission=submission, parent=reddit_comment, comment=reply)


class RedditToLemmyCommunity(models.Model):
    subreddit = models.ForeignKey(RedditCommunity, on_delete=models.CASCADE)
    lemmy_community = models.ForeignKey(LemmyCommunity, on_delete=models.CASCADE)

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
        unique_together = ("reddit_submission", "lemmy_post_id")


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
