from allauth.socialaccount.models import SocialAccount, SocialToken
from django.conf import settings
from django.db import models

from fediverser.apps.core.settings import app_settings
from fediverser.apps.lemmy.services import LocalUserProxy

from .activitypub import Community, Person
from .feeds import CommunityFeed
from .mapping import ChangeRequest
from .reddit import RedditCommunity, RedditOAuthScopes, make_reddit_user_client


class UserAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="account", on_delete=models.CASCADE
    )
    community_feeds = models.ManyToManyField(CommunityFeed)
    lemmy_local_username = models.CharField(max_length=255, unique=True, null=True, blank=True)
    tracked_subreddits = models.ManyToManyField(RedditCommunity)

    @property
    def recommended_communities(self):
        return Community.objects.filter(
            recommendations__subreddit__in=self.tracked_subreddits.all()
        )

    @property
    def subreddits_without_recommendation(self):
        return self.tracked_subreddits.filter(recommendations__isnull=True)

    @property
    def has_connected_activitypub_accounts(self):
        return self.connected_activitypub_accounts.exists()

    @property
    def lemmy_client(self):
        lemmy_user = self.lemmy_local_user
        return lemmy_user and lemmy_user.make_lemmy_client()

    @property
    def lemmy_local_user(self):
        if not settings.FEDIVERSER_ENABLE_LEMMY_INTEGRATION:
            return None

        return LocalUserProxy.objects.filter(person__name=self.lemmy_local_username).first()

    @property
    def connected_social_accounts(self):
        return self.user.socialaccount_set.all()

    @property
    def can_send_reddit_private_messages(self):
        return self.user.socialaccount_set.filter(
            reddit_scopes__scope=RedditOAuthScopes.CREATE_PRIVATE_MESSAGES
        ).exists()

    def get_reddit_client(self):
        social_token = SocialToken.objects.filter(account__user=self.user).first()

        return social_token and make_reddit_user_client(
            social_application=app_settings.reddit_social_application,
            refresh_token=social_token.token_secret,
        )

    def check_lemmy_password(self, cleartext):
        return bool(self.lemmy_local_user) and self.lemmy_local_user.check_password(cleartext)


class RedditAccountAuthorizedScope(models.Model):
    social_account = models.ForeignKey(
        SocialAccount, related_name="reddit_scopes", on_delete=models.CASCADE
    )
    scope = models.CharField(max_length=32, choices=RedditOAuthScopes.choices)


class ConnectedActivityPubAccount(models.Model):
    account = models.ForeignKey(
        UserAccount, related_name="connected_activitypub_accounts", on_delete=models.CASCADE
    )
    actor = models.ForeignKey(
        Person, related_name="connected_portal_accounts", on_delete=models.CASCADE
    )


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


__all__ = (
    "UserAccount",
    "CommunityAmbassador",
    "CommunityAmbassadorApplication",
    "ConnectedActivityPubAccount",
    "RedditAccountAuthorizedScope",
)
