import datetime
import logging

import feedparser
from django.db import models
from django.utils import timezone
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel
from taggit.managers import TaggableManager

from .activitypub import Community

EPOCH = datetime.datetime.fromtimestamp(0)

logger = logging.getLogger(__name__)


def parsed_datetime(time_tuple):
    return timezone.make_aware(datetime.datetime(*time_tuple[:6]))


class AbstractFeedAuthorData(models.Model):
    author_name = models.TextField(null=True, blank=True)
    author_email = models.EmailField(null=True, blank=True)
    author_link = models.URLField(null=True, blank=True)

    class Meta:
        abstract = True


class Feed(TimeStampedModel, AbstractFeedAuthorData):
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

    def fetch(self):
        result = feedparser.parse(self.url)
        last_checked_time_tuple = (self.last_checked or EPOCH).timetuple()
        for entry in result.entries:
            if entry.get("updated_parsed") > last_checked_time_tuple:
                author_detail = entry.get("author_detail", {})
                try:
                    content = entry.content[0].value
                except (AttributeError, IndexError):
                    content = None

                feed_link, _ = Entry.objects.get_or_create(
                    feed=self,
                    url=entry["url"],
                    defaults={
                        "title": entry.title,
                        "summary": entry.summary,
                        "content": content,
                        "created": parsed_datetime(entry.published_parsed),
                        "modified": parsed_datetime(entry.updated_parsed),
                        "author_name": author_detail.get("name"),
                        "author_link": author_detail.get("link"),
                        "author_email": author_detail.get("email"),
                        "guid": entry.get("id") or entry.get("post-id"),
                    },
                )
            else:
                logger.info(f"Skipping {entry.id}")
        self.last_checked = timezone.now()
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
                language=getattr(result.feed, "language", None),
                etag=result.etag,
            )
        return feed


class Entry(TimeStampedModel, AbstractFeedAuthorData):
    feed = models.ForeignKey(Feed, on_delete=models.PROTECT)
    url = models.URLField(unique=True)
    title = models.TextField(null=True, blank=True)
    guid = models.CharField(max_length=500, null=True, blank=True, db_index=True)
    summary = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    copyright = models.TextField(null=True, blank=True)
    tags = TaggableManager()


class CommunityFeed(models.Model):
    community = models.ForeignKey(Community, related_name="feeds", on_delete=models.CASCADE)
    feed = models.ForeignKey(Feed, related_name="communities", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("community", "feed")


__all__ = ("Feed", "Entry", "CommunityFeed")
