import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from model_utils import Choices
from model_utils.managers import InheritanceManager, QueryManager
from model_utils.models import StatusModel, TimeStampedModel
from wagtailautocomplete.edit_handlers import AutocompletePanel

from .activitypub import Community, Instance
from .common import COMMUNITY_STATUSES, INSTANCE_STATUSES, Category
from .reddit import RedditCommunity

logger = logging.getLogger(__name__)
User = get_user_model()


class RedditAlternativeRecommendation(TimeStampedModel):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="recommendations", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="recommendations", on_delete=models.CASCADE
    )
    panels = [AutocompletePanel("subreddit"), AutocompletePanel("community")]

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
        return f"Change request #{self.id}"

    def apply(self):
        raise NotImplementedError("Child classes need to implement this method")

    def accept(self):
        self.apply()
        self.status = self.STATUS.accepted
        self.save()

    def reject(self):
        self.status = self.STATUS.rejected
        self.save()


class SetRedditCommunityCategory(ChangeRequest):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="category_change_requests", on_delete=models.CASCADE
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend {self.category.name} as category {self.subreddit}"

    def apply(self):
        self.subreddit.category = self.category
        self.subreddit.save()


class RecommendCommunity(ChangeRequest):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="recommendation_requests", on_delete=models.CASCADE
    )
    community = models.ForeignKey(Community, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend {self.community.fqdn} as alternative to {self.subreddit}"

    def apply(self):
        self.subreddit.recommended_communities.add(self.community)


class SetRedditCommunityStatus(ChangeRequest):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="status_change_requests", on_delete=models.CASCADE
    )
    community_status = models.CharField(max_length=20, choices=COMMUNITY_STATUSES)

    @property
    def description(self):
        return f"Mark {self.subreddit.name} as {self.get_community_status_display()}"

    def apply(self):
        self.subreddit.status = self.community_status
        self.subreddit.save()


class SetCommunityStatus(ChangeRequest):
    community = models.ForeignKey(
        Community, related_name="status_change_requests", on_delete=models.CASCADE
    )
    community_status = models.CharField(max_length=20, choices=COMMUNITY_STATUSES)

    @property
    def description(self):
        return f"Mark {self.community.fqdn} as {self.get_community_status_display()}"

    def apply(self):
        self.community.status = self.community_status
        self.community.save()


class SetCommunityCategory(ChangeRequest):
    community = models.ForeignKey(
        Community, related_name="category_change_requests", on_delete=models.CASCADE
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend category {self.category.name} to {self.community}"

    def apply(self):
        self.community.category = self.category
        self.community.save()


class SetInstanceStatus(ChangeRequest):
    instance = models.ForeignKey(
        Instance, related_name="status_change_requests", on_delete=models.CASCADE
    )
    server_status = models.CharField(max_length=20, choices=INSTANCE_STATUSES)

    @property
    def description(self):
        return f"Mark {self.instance.domain} as {self.get_server_status_display()}"

    def apply(self):
        self.instance.status = self.server_status
        self.instance.save()


class SetInstanceCategory(ChangeRequest):
    instance = models.ForeignKey(
        Instance, related_name="category_change_requests", on_delete=models.CASCADE
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    @property
    def description(self):
        return f"Recommend category {self.category.name} to {self.instance}"

    def apply(self):
        self.instance.category = self.category
        self.instance.save()


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
