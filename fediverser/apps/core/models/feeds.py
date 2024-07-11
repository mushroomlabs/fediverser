import datetime
import logging

import feedparser
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db import models
from django.template.defaultfilters import slugify
from django.utils import timezone
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from .activitypub import Community

EPOCH = timezone.make_aware(datetime.datetime.fromtimestamp(0))

logger = logging.getLogger(__name__)


def parsed_datetime(time_tuple):
    return timezone.make_aware(datetime.datetime(*time_tuple[:6]))


class Feed(TimeStampedModel):
    FETCH_INTERVAL = datetime.timedelta(seconds=15 * 60)

    url = models.URLField(unique=True)
    title = models.TextField(null=True)
    subtitle = models.TextField(null=True, blank=True)
    etag = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    last_fetched = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(db_index=True, default=True)

    objects = models.Manager()
    active = QueryManager(is_active=True)

    def __str__(self):
        if not self.title:
            return self.url

        return f"{self.title} ({self.url})"

    def fetch(self, force=False):
        logger.info(f"Feed {self.url} requested")

        last_checked = self.last_fetched or EPOCH
        now = timezone.now()
        if not force and (now - last_checked < Feed.FETCH_INTERVAL):
            time_ago = naturaltime(last_checked)
            logger.info(f"Skipping {self.url} because it was fetched only {time_ago}")
            return

        result = feedparser.parse(self.url)
        for entry in result.entries:
            if not entry.get("link"):
                continue

            entry_age = now - parsed_datetime(entry.updated_parsed)
            try:
                assert entry_age < Entry.MAX_AGE, "too old"
                assert parsed_datetime(entry.updated_parsed) > last_checked, "already checked"
                Entry.make(entry=entry, feed=self)
            except AssertionError as exc:
                if force:
                    Entry.make(entry=entry, feed=self)
                else:
                    logger.info(f"Skipping entry {entry.link}: {exc}")

        self.last_fetched = now
        self.save()

    @classmethod
    def make(cls, url):
        feed = cls.objects.filter(url=url).first()
        if not feed:
            logger.info(f"{url} is not a registered feed")
            result = feedparser.parse(url)
            feed = cls.objects.create(
                url=url,
                title=result.feed.title,
                subtitle=getattr(result.feed, "subtitle", None),
                etag=getattr(result, "etag", None),
            )
        return feed


class Entry(TimeStampedModel):
    MAX_AGE = datetime.timedelta(days=7)

    feed = models.ForeignKey(Feed, on_delete=models.PROTECT)
    link = models.URLField(unique=True)
    title = models.TextField(null=True, blank=True)
    guid = models.CharField(max_length=500, null=True, blank=True, db_index=True)
    summary = models.TextField(null=True, blank=True)
    tags = TaggableManager()

    def __str__(self):
        return self.link

    @classmethod
    def make(cls, entry, feed):
        link = entry.get("link")
        tag_list = entry.get("tags", [])
        tags = [t.get("term") if isinstance(t, dict) else str(t) for t in tag_list]
        obj, _ = cls.objects.update_or_create(
            feed=feed,
            link=link,
            defaults={
                "title": entry.title,
                "summary": entry.summary,
                "created": parsed_datetime(entry.published_parsed),
                "modified": parsed_datetime(entry.updated_parsed),
                "guid": entry.get("id") or entry.get("post-id"),
                "tags": ", ".join([slugify(tag) for tag in tags]),
            },
        )

        return obj

    class Meta:
        verbose_name_plural = "Feed Entries"


class CommunityFeed(models.Model):
    community = models.ForeignKey(Community, related_name="feeds", on_delete=models.CASCADE)
    feed = models.ForeignKey(Feed, related_name="communities", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.feed.url} (feed for {self.community.fqdn})"

    class Meta:
        unique_together = ("community", "feed")


__all__ = ("Feed", "Entry", "CommunityFeed")
