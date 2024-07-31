import secrets
from datetime import timedelta

from django.db import models
from django.utils import timezone
from invitations.app_settings import app_settings as invitations_settings
from invitations.base_invitation import AbstractBaseInvitation
from invitations.managers import BaseInvitationManager
from model_utils.models import TimeStampedModel

from .activitypub import Community
from .reddit import RedditAccount, RedditCommunity


class InviteTemplate(models.Model):
    name = models.CharField(unique=True, max_length=100)
    message = models.TextField()

    def __str__(self):
        return self.name


class CommunityInviteTemplate(InviteTemplate):
    """
    A template text for sending automated invites to a given community
    """

    subreddit = models.ForeignKey(
        RedditCommunity, related_name="invite_templates", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="invite_templates", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("subreddit", "community")


class RedditorInvite(AbstractBaseInvitation):
    """
    A record to indicate when a message inviting a redditor has been sent
    """

    redditor = models.ForeignKey(RedditAccount, related_name="invites", on_delete=models.CASCADE)
    template = models.ForeignKey(
        InviteTemplate, related_name="invites_sent", null=True, on_delete=models.SET_NULL
    )

    objects = BaseInvitationManager()

    @classmethod
    def create(cls, redditor, inviter=None, **kw):
        default_key = "".join([c for c in secrets.token_urlsafe(48) if c not in ("_", "-")])
        key = kw.pop("key", default_key)
        return cls.objects.create(redditor=redditor, inviter=inviter, key=key.lower())

    def key_expired(self):
        threshold = timezone.now() - timedelta(days=invitations_settings.INVITATION_EXPIRY)
        return self.accepted or (self.sent is not None and self.sent < threshold)

    def send_invitation(self, request, **kwargs):
        raise NotImplementedError("You should implement the send_invitation method")

    def __str__(self):
        return f"Invite from {self.inviter.username} to {self.redditor}"


class RedditorDeclinedInvite(TimeStampedModel):
    class Reasons(models.TextChoices):
        SUPPORTER = ("supporter", "I fully support Reddit and their management")
        EMPLOYEE = ("employee", "I work for Reddit")
        INVESTOR = ("investor", "I am an investor in Reddit")
        ALREADY_MIGRATED = (
            "already_migrated",
            "Helping with migration efforts on another site",
        )
        NOT_INTERESTED = ("not_interested", "Not interested in contributing to migration efforts")
        OTHER = ("other", "Other")

    redditor = models.ForeignKey(
        RedditAccount, related_name="declined_invites", on_delete=models.CASCADE
    )
    key = models.CharField(max_length=64, unique=True)
    reason = models.CharField(max_length=16, choices=Reasons.choices, default=Reasons.SUPPORTER)
    note = models.TextField(null=True, blank=True, help_text="Anything you like to share?")


__all__ = ("InviteTemplate", "CommunityInviteTemplate", "RedditorInvite", "RedditorDeclinedInvite")
