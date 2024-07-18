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

    @classmethod
    def current(cls):
        NODE_CONFIGURATION = {
            "portal_url": app_settings.Portal.url,
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

        instance, _ = cls.objects.update_or_create(instance=connected_instance, defaults=data)
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
    reddit_account = models.ForeignKey(RedditAccount, on_delete=models.CASCADE)
    actor = models.ForeignKey(Person, on_delete=models.CASCADE)


class ChangeFeedEntry(TimeStampedModel):
    published_by = models.ForeignKey(
        FediversedInstance, related_name="published_feed_entries", on_delete=models.CASCADE
    )
    objects = InheritanceManager()

    @property
    def description(self):
        return f"Change #{self.id}"


class ConnectedRedditAccountEntry(ChangeFeedEntry):
    connection = models.ForeignKey(
        ConnectedRedditAccount, related_name="feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        return f"{self.connection.reddit_account} is on the Fediverse at {self.actor.url}"


class EndorsementEntry(ChangeFeedEntry):
    endorsemement = models.ForeignKey(
        Endorsement, related_name="feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        return f"{self.connection.reddit_account} is on the Fediverse at {self.actor.url}"


__all__ = (
    "FediversedInstance",
    "Endorsement",
    "ConnectedRedditAccount",
    "ChangeFeedEntry",
    "EndorsementEntry",
    "ConnectedRedditAccountEntry",
)
