from django.conf import settings
from django.db import models

from fediverser.apps.lemmy.services import LocalUserProxy

from .activitypub import Community
from .feeds import CommunityFeed
from .mapping import ChangeRequest
from .reddit import RedditAccount


class UserAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="account", on_delete=models.CASCADE
    )
    reddit_account = models.OneToOneField(
        RedditAccount,
        related_name="portal_account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    community_feeds = models.ManyToManyField(CommunityFeed)
    lemmy_local_username = models.CharField(max_length=255, unique=True, null=True, blank=True)

    @property
    def lemmy_local_user(self):
        return LocalUserProxy.objects.filter(person__name=self.lemmy_local_username).first()

    def check_lemmy_password(self, cleartext):
        return bool(self.lemmy_local_user) and self.lemmy_local_user.check_password(cleartext)


class CommunityAmbassador(models.Model):
    account = models.ForeignKey(
        UserAccount, related_name="representing_communities", on_delete=models.CASCADE
    )
    community = models.ForeignKey(Community, related_name="ambassadors", on_delete=models.CASCADE)

    class Meta:
        unique_together = ("account", "community")


class CommunityAmbassadorApplication(ChangeRequest):
    community = models.ForeignKey(
        Community, related_name="ambassador_applications", on_delete=models.CASCADE
    )

    @property
    def description(self):
        return f"Submit Application to become an ambassador for {self.community}"

    def apply(self):
        self.requester.account.representing_communities.create(community=self.community)


__all__ = ("UserAccount", "CommunityAmbassador", "CommunityAmbassadorApplication")
