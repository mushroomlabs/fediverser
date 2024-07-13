import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from model_utils import Choices
from model_utils.managers import InheritanceManager, QueryManager
from model_utils.models import StatusModel

from .activitypub import Community, Instance
from .common import Category
from .reddit import RedditCommunity

logger = logging.getLogger(__name__)
User = get_user_model()


class RedditToCommunityRecommendation(models.Model):
    subreddit = models.ForeignKey(
        RedditCommunity, related_name="recommendations", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="recommendations", on_delete=models.CASCADE
    )

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
        return f"Recommend {self.category.name} as category to {self.subreddit}"

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
        self.subreddit.recommendations.create(community=self.community)


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
