import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django_countries.fields import CountryField
from model_utils import Choices
from model_utils.managers import InheritanceManager, QueryManager
from model_utils.models import StatusModel
from taggit.managers import TaggableManager
from wagtail.images.models import Image
from wagtail.snippets.models import register_snippet

from .activitypub import Community, Instance
from .common import COMMUNITY_STATUSES, INSTANCE_STATUSES, Category
from .reddit import RedditCommunity

logger = logging.getLogger(__name__)
User = get_user_model()


class AbstractAnnotation(models.Model):
    """
    Annotation entries are meant to provide metadata about the data being tracked
    """

    locked = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    notes = models.TextField()

    class Meta:
        abstract = True


class InstanceAnnotation(AbstractAnnotation):
    instance = models.OneToOneField(Instance, related_name="annotation", on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=INSTANCE_STATUSES, default=INSTANCE_STATUSES.active
    )

    def __str__(self):
        return self.instance.domain


class CommunityAnnotation(AbstractAnnotation):
    community = models.OneToOneField(
        Community, related_name="annotation", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20, choices=COMMUNITY_STATUSES, default=COMMUNITY_STATUSES.active
    )
    category = models.ForeignKey(
        Category,
        related_name="community_annotations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return str(self.community)


class SubredditAnnotation(AbstractAnnotation):
    subreddit = models.OneToOneField(
        RedditCommunity, related_name="annotation", on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=20, choices=COMMUNITY_STATUSES, default=COMMUNITY_STATUSES.active
    )
    category = models.ForeignKey(
        Category,
        related_name="subreddit_annotations",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    def __str__(self):
        return str(self.subreddit)


@register_snippet
class Topic(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=64, unique=True)
    description = models.TextField()
    icon = models.ForeignKey(
        Image, related_name="topics_icons", null=True, blank=True, on_delete=models.SET_NULL
    )
    tags = TaggableManager()

    def __str__(self):
        return self.name


class InstanceTopic(models.Model):
    instance = models.ForeignKey(Instance, related_name="topics", on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, related_name="instances", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("instance", "topic")


class InstanceCountry(models.Model):
    instance = models.ForeignKey(
        Instance, related_name="related_countries", on_delete=models.CASCADE
    )
    country = CountryField()

    class Meta:
        unique_together = ("instance", "country")


class InstanceExtraInformation(models.Model):
    instance = models.OneToOneField(Instance, related_name="extra", on_delete=models.CASCADE)
    invite_only = models.BooleanField(null=True, blank=True)
    application_required = models.BooleanField(null=True, blank=True)
    payment_required = models.BooleanField(default=False)
    abandoned = models.BooleanField(default=False)


class RedditToCommunityRecommendation(models.Model):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="recommendations", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="recommendations", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Recommendation of {self.community} as alternative to {self.subreddit}"

    class Meta:
        unique_together = ("subreddit", "community")


class ChangeRequest(StatusModel):
    STATUS = Choices("requested", "accepted", "rejected")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="change_requests", on_delete=models.CASCADE
    )
    objects = InheritanceManager()
    pending = QueryManager(status=STATUS.requested)

    @property
    def description(self):
        return f"Change request #{self.id} {self.__class__.__name__}"

    @property
    def auto_accept(self):
        return self.requester.is_staff

    def apply(self):
        raise NotImplementedError("Child classes need to implement this method")

    def accept(self):
        self.apply()
        self.status = self.STATUS.accepted
        self.save()

    def reject(self):
        self.status = self.STATUS.rejected
        self.save()


class RecommendCommunity(ChangeRequest):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="recommendation_requests", on_delete=models.CASCADE
    )
    community = models.ForeignKey(Community, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend {self.community.fqdn} as alternative to {self.subreddit}"

    def apply(self):
        self.subreddit.recommendations.create(community=self.community)


class SetRedditCommunityCategory(ChangeRequest):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="category_change_requests", on_delete=models.CASCADE
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend {self.category.name} as category to {self.subreddit}"

    def apply(self):
        SubredditAnnotation.objects.update_or_create(
            subreddit=self.subreddit, defaults={"category": self.category}
        )


class SetCommunityCategory(ChangeRequest):
    community = models.ForeignKey(
        Community, related_name="category_change_requests", on_delete=models.CASCADE
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend category {self.category.name} to {self.community}"

    def apply(self):
        CommunityAnnotation.objects.update_or_create(
            community=self.community, defaults={"category": self.category}
        )


class SetInstanceCategory(ChangeRequest):
    instance = models.ForeignKey(
        Instance, related_name="category_change_requests", on_delete=models.CASCADE
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend category {self.category.name} to {self.instance}"

    def apply(self):
        InstanceAnnotation.objects.update_or_create(
            instance=self.instance, defaults={"category": self.category}
        )


class SetInstanceCountry(ChangeRequest):
    instance = models.ForeignKey(
        Instance, related_name="country_selection_requests", on_delete=models.CASCADE
    )
    country = CountryField()

    @property
    def description(self):
        return f"Set {self.instance} as for people from {self.country.name}"

    def apply(self):
        InstanceCountry.objects.get_or_create(instance=self.instance, country=self.country)


class CommunityRequest(StatusModel):
    STATUS = Choices("requested", "accepted", "rejected")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="community_requests", on_delete=models.CASCADE
    )
    instance = models.ForeignKey(
        Instance, related_name="community_requests", on_delete=models.CASCADE
    )
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="community_requests", on_delete=models.CASCADE
    )
    fulfilled_by = models.ForeignKey(
        Community,
        related_name="creation_requests",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )


__all__ = (
    "InstanceAnnotation",
    "CommunityAnnotation",
    "SubredditAnnotation",
    "Topic",
    "InstanceCountry",
    "InstanceTopic",
    "InstanceExtraInformation",
    "RedditToCommunityRecommendation",
    "ChangeRequest",
    "SetRedditCommunityCategory",
    "RecommendCommunity",
    "SetCommunityCategory",
    "SetInstanceCategory",
    "SetInstanceCountry",
    "CommunityRequest",
)
