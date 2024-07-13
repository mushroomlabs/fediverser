from django.db import models
from model_utils.models import TimeStampedModel

from .activitypub import Community
from .reddit import RedditAccount, RedditCommunity


class CommunityInviteTemplate(models.Model):
    """
    A template text for sending automated invites to a given community
    """

    subreddit = models.ForeignKey(
        RedditCommunity, related_name="invite_templates", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="invite_templates", on_delete=models.CASCADE
    )
    message = models.TextField()

    class Meta:
        unique_together = ("subreddit", "community")


class CommunityInvite(TimeStampedModel):
    """
    A record to indicate when a message inviting a redditor has been sent
    """

    redditor = models.ForeignKey(RedditAccount, related_name="invites", on_delete=models.CASCADE)
    template = models.ForeignKey(
        CommunityInviteTemplate,
        related_name="invites_sent",
        null=True,
        on_delete=models.SET_NULL,
    )


__all__ = ("CommunityInviteTemplate", "CommunityInvite")
