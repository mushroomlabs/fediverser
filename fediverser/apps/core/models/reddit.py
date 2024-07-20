import datetime
import logging
from typing import Optional

import praw
from django.conf import settings
from django.db import models
from django.db.models import Max, Q
from django.db.utils import DataError
from django.utils import timezone
from django.utils.timezone import make_aware
from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException
from model_utils.managers import QueryManager
from model_utils.models import StatusModel, TimeStampedModel
from praw import Reddit
from prawcore.exceptions import Forbidden, NotFound, UnavailableForLegalReasons
from pythorhead.types import LanguageType
from taggit.managers import TaggableManager
from wagtail.admin.panels import FieldPanel

from ..choices import SOURCE_CONTENT_STATUSES
from .common import COMMUNITY_STATUSES, Category

logger = logging.getLogger(__name__)


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


class RejectedComment(Exception):
    pass


class RejectedPost(Exception):
    pass


class RedditCommunity(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(
        Category,
        related_name="subreddits",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    description = models.TextField(null=True, blank=True)
    over18 = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=COMMUNITY_STATUSES, blank=True, null=True)
    metadata = models.JSONField(null=True, blank=True)
    tags = TaggableManager(blank=True)
    locked = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True)

    panels = [
        FieldPanel("category"),
        FieldPanel("status"),
        FieldPanel("tags"),
        FieldPanel("locked"),
        FieldPanel("hidden"),
    ]
    autocomplete_search_field = "name"

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
    def advertiser_category(self):
        try:
            return self.metadata["advertiser_category"]
        except (TypeError, KeyError):
            return None

    @property
    def original_description(self):
        try:
            return self.metadata["description"]
        except (TypeError, KeyError):
            return None

    @property
    def reported_subscribers(self):
        try:
            return self.metadata["subscribers"]
        except (TypeError, KeyError):
            return None

    @property
    def banner_image_url(self):
        return self.metadata and self.metadata.get("banner_img") or None

    @property
    def header_image_url(self):
        return self.metadata and self.metadata.get("header_img") or None

    @property
    def logo_image_url(self):
        return self.metadata and self.metadata.get("icon_img") or None

    @property
    def full_reddit_url(self):
        return f"https://reddit.com/r/{self.name}"

    @property
    def praw_object(self):
        reddit = make_reddit_client()
        return reddit.subreddit(self.name)

    def fetch_new_posts(self):
        client = make_reddit_client()
        most_recent_post = self.most_recent_post
        posts = [p for p in client.subreddit(self.name).new()]

        if most_recent_post is not None:
            posts = [p for p in posts if p.created_utc > most_recent_post.timestamp()]

        for post in posts:
            RedditSubmission.make(subreddit=self, post=post)

        self.last_synced_at = timezone.now()
        self.save()

    def get_metadata(self):
        client = make_reddit_client()
        try:
            praw_subreddit = client.subreddit(self.name)
            data = praw_subreddit._fetch_data()
            self.metadata = data.get("data")
        except UnavailableForLegalReasons:
            self.metadata = None
        except (Forbidden, NotFound):
            self.hidden = True
            self.metadata = None
        self.save()

    def autocomplete_label(self):
        return self.name

    def __str__(self):
        return f"/r/{self.name}"

    @classmethod
    def autocomplete_custom_queryset_filter(cls, search_term: str):
        field_name = "name"
        filter_kwargs = dict()
        filter_kwargs[field_name + "__contains"] = search_term
        return cls.objects.filter(**filter_kwargs)

    @classmethod
    def fetch(cls, name):
        client = make_reddit_client()
        try:
            praw_subreddit = client.subreddit(name)
            data = praw_subreddit._fetch_data().get("data")
            subreddit, _ = cls.objects.get_or_create(
                name=praw_subreddit.display_name,
                defaults={"description": data.get("description"), "over18": data.get("over18")},
            )
        except UnavailableForLegalReasons:
            subreddit, _ = cls.objects.update_or_create(name=name, defaults={"metadata": None})

        except (Forbidden, NotFound):
            subreddit, _ = cls.objects.update_or_create(
                name=name, defaults={"hidden": True, "metadata": {}}
            )
        return subreddit

    class Meta:
        verbose_name_plural = "Subreddit"
        verbose_name_plural = "Subreddits"


class RedditAccount(TimeStampedModel):
    username = models.CharField(unique=True, max_length=60)
    marked_as_spammer = models.BooleanField(default=False)
    marked_as_bot = models.BooleanField(default=False)
    suspended = models.BooleanField(default=False)
    blocked = models.BooleanField(default=False)
    subreddits = models.ManyToManyField(RedditCommunity, blank=True)

    @property
    def can_send_invite(self):
        now = timezone.now()
        return all(
            [
                not self.marked_as_spammer,
                not self.invites.filter(created__gte=now - datetime.timedelta(days=7)).exists(),
            ]
        )

    @property
    def is_claimed(self):
        return getattr(self, "account", None) is not None

    @property
    def is_shadow_account(self):
        return getattr(self, "account", None) is None

    @property
    def reddit_view_url(self):
        return f"https://reddit.com/u/{self.username}"

    @classmethod
    def make(cls, redditor: praw.models.Redditor):
        if redditor is None:
            return None

        defaults = {
            "suspended": getattr(redditor, "is_suspended", False),
            "blocked": getattr(redditor, "is_blocked", False),
        }
        if hasattr(redditor, "created_utc"):
            created_date = timezone.make_aware(
                datetime.datetime.fromtimestamp(redditor.created_utc)
            )
            defaults["created"] = created_date
            defaults["modified"] = created_date

        account, _ = cls.objects.update_or_create(username=redditor.name, defaults=defaults)
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
    MAX_AGE = datetime.timedelta(days=5)

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

    objects = models.Manager()
    repostable = QueryManager(
        Q(author__marked_as_bot=False)
        & Q(author__marked_as_spammer=False)
        & Q(removed=False)
        & Q(quarantined=False)
        & ~Q(selftext="[removed]")
    )
    spam = QueryManager(Q(author__marked_as_spammer=True) | Q(marked_as_spam=True))
    from_bots = QueryManager(author__marked_as_bot=True)

    @property
    def has_self_text(self):
        return self.selftext is not None and self.selftext.strip()

    @property
    def reddit_view_url(self):
        return f"https://reddit.com/r/{self.subreddit.name}/comments/{self.id}"

    @property
    def is_link_post(self):
        return not any(
            [
                self.is_cross_post,
                self.is_media_hosted_on_reddit,
                self.url.startswith("https://reddit.com"),
                self.url.startswith("https://www.reddit.com"),
            ]
        )

    @property
    def is_self_post(self):
        reddit_urls = ["https://reddit.com", "https://www.reddit.com"]
        return any([self.url.startswith(root) for root in reddit_urls])

    @property
    def is_cross_post(self):
        return self.url.startswith("/r/")

    @property
    def can_be_submitted_automatically(self):
        return all(
            [
                settings.FEDIVERSER_ENABLE_LEMMY_INTEGRATION,
                not self.over_18,
                not self.banned_at,
                not self.quarantined,
                not self.removed,
                not self.is_cross_post,
                self.url is not None and not self.url.startswith("https://twitter.com"),
                self.url is not None and not self.url.startswith("https://x.com"),
                not self.is_video_hosted_on_reddit,
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

    def validate(self):
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


__all__ = ("RedditAccount", "RedditSubmission", "RedditComment", "RedditCommunity")
