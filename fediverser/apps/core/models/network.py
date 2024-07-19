from urllib.parse import urlparse

from django.db import models
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel

from fediverser.apps.core.models.common import AP_SERVER_SOFTWARE, INSTANCE_STATUSES
from fediverser.apps.core.settings import app_settings
from fediverser.apps.lemmy.services import InstanceProxy
from fediverser.apps.lemmy.settings import app_settings as lemmy_settings

from .activitypub import Instance, Person
from .common import make_http_client
from .mapping import RedditToCommunityRecommendation
from .reddit import RedditAccount


class FediversedInstance(models.Model):
    instance = models.OneToOneField(
        Instance,
        related_name="fediverser_configuration",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    portal_url = models.URLField(null=True, blank=True)
    allows_reddit_signup = models.BooleanField(default=True)
    allows_reddit_mirrored_content = models.BooleanField(default=False)
    creates_reddit_mirror_bots = models.BooleanField(default=False)
    accepts_community_requests = models.BooleanField(
        default=False, help_text="Accepts Community Requests"
    )

    def submit_registration(self, partner):
        if self == partner:
            raise ValueError("Attempt to submit registration to itself")

        client = make_http_client()
        client.headers.update({"Content-Type": "application/json"})
        url = f"{partner.portal_url}/api/fediverser-instances"
        response = client.post(url, json={"portal_url": self.portal_url})
        response.raise_for_status()

    def endorse(self, partner):
        if self == partner:
            raise ValueError("Attempt to add endorsement to itself")

        endorsement, _ = Endorsement.objects.get_or_create(endorser=self, endorsed=partner)
        entry, _ = EndorsementEntry.objects.get_or_create(
            endorsement=endorsement, published_by=self
        )
        return endorsement

    @property
    def trusted_instances(self):
        return FediversedInstance.objects.filter(endorsed_instances__endorser=self)

    @property
    def trusted_by(self):
        return FediversedInstance.objects.filter(endorsing_instances__endorsed=self)

    def __str__(self):
        return self.portal_url

    @classmethod
    def current(cls):
        NODE_CONFIGURATION = {
            "accepts_community_requests": app_settings.Portal.accepts_community_requests,
            "allows_reddit_signup": app_settings.Portal.signup_with_reddit,
            "allows_reddit_mirrored_content": lemmy_settings.Instance.reddit_mirror_bots_enabled,
            "creates_reddit_mirror_bots": app_settings.Reddit.mirroring_enabled,
        }
        lemmy_instance = InstanceProxy.get_connected_instance()

        if lemmy_instance is not None:
            instance, _ = Instance.objects.get_or_create(
                domain=lemmy_instance.domain,
                defaults={
                    "software": AP_SERVER_SOFTWARE.lemmy,
                    "status": INSTANCE_STATUSES.active,
                },
            )
        else:
            instance = None

        fediversed_instance, _ = cls.objects.update_or_create(
            portal_url=app_settings.Portal.url,
            instance=instance,
            defaults=NODE_CONFIGURATION,
        )
        return fediversed_instance

    @classmethod
    def fetch(cls, url):
        url = url.removesuffix("/")
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme
        domain = parsed_url.hostname

        client = make_http_client()

        nodeinfo_url = f"{scheme}://{domain}/api/nodeinfo"
        response = client.get(nodeinfo_url, headers={"Accept": "application/json"})
        response.raise_for_status()
        data = response.json()
        instance_data = data.pop("instance", None)

        connected_instance = instance_data and Instance.fetch(instance_data["url"])
        data["instance"] = connected_instance

        instance, _ = cls.objects.update_or_create(portal_url=url, defaults=data)
        return instance


class Endorsement(models.Model):
    endorser = models.ForeignKey(
        FediversedInstance, related_name="endorsing_instances", on_delete=models.CASCADE
    )
    endorsed = models.ForeignKey(
        FediversedInstance, related_name="endorsed_instances", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("endorser", "endorsed")


class ConnectedRedditAccount(models.Model):
    reddit_account = models.ForeignKey(
        RedditAccount, related_name="connected_activitypub_accounts", on_delete=models.CASCADE
    )
    actor = models.ForeignKey(
        Person, related_name="connected_reddit_accounts", on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("reddit_account", "actor")


class ChangeFeedEntry(TimeStampedModel):
    TYPE = None
    published_by = models.ForeignKey(
        FediversedInstance, related_name="published_feed_entries", on_delete=models.CASCADE
    )
    objects = InheritanceManager()

    @property
    def description(self):
        return f"Change #{self.id}:"


class ConnectedRedditAccountEntry(ChangeFeedEntry):
    TYPE = "connection:reddit"
    connection = models.ForeignKey(
        ConnectedRedditAccount, related_name="feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        actor_url = self.connection.actor.url
        return f"{self.connection.reddit_account} connected as {actor_url}"


class EndorsementEntry(ChangeFeedEntry):
    TYPE = "endorsement"
    endorsement = models.ForeignKey(
        Endorsement, related_name="feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        return f"{self.endorsement.endorser} endorses {self.endorsement.endorsed}"


class RedditToCommunityRecommendationEntry(ChangeFeedEntry):
    TYPE = "recommendation:group"

    recommendation = models.ForeignKey(
        RedditToCommunityRecommendation, related_name="feed_entries", on_delete=models.CASCADE
    )


__all__ = (
    "FediversedInstance",
    "Endorsement",
    "ConnectedRedditAccount",
    "ChangeFeedEntry",
    "EndorsementEntry",
    "ConnectedRedditAccountEntry",
    "RedditToCommunityRecommendationEntry",
)
