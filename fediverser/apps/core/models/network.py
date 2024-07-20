import logging
from urllib.parse import urlencode, urlparse

from django.db import models
from django.utils import timezone
from model_utils.managers import InheritanceManager
from model_utils.models import TimeStampedModel

from fediverser.apps.core.models.common import AP_SERVER_SOFTWARE, INSTANCE_STATUSES
from fediverser.apps.core.settings import app_settings
from fediverser.apps.lemmy.services import InstanceProxy
from fediverser.apps.lemmy.settings import app_settings as lemmy_settings

from .activitypub import Community, Instance, Person
from .common import make_http_client
from .reddit import RedditAccount, RedditCommunity

logger = logging.getLogger(__name__)


class FediversedInstanceQuerySet(models.QuerySet):
    def exclude_current(self):
        return self.exclude(portal_url=app_settings.Portal.url)

    def get_current(self):
        return self.filter(portal_url=app_settings.Portal.url).first()


class FediversedInstancePartnerModelManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.exclude(portal_url=app_settings.Portal.url)


class FediversedInstance(models.Model):
    instance = models.OneToOneField(
        Instance,
        related_name="fediverser_configuration",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    portal_url = models.URLField(unique=True)

    allows_reddit_signup = models.BooleanField(default=True)
    allows_reddit_mirrored_content = models.BooleanField(default=False)
    creates_reddit_mirror_bots = models.BooleanField(default=False)
    accepts_community_requests = models.BooleanField(
        default=False, help_text="Accepts Community Requests"
    )

    objects = FediversedInstanceQuerySet.as_manager()
    partners = FediversedInstancePartnerModelManager()

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

    def sync_change_feeds(self, since=None):
        client = make_http_client()
        url = f"{self.portal_url}/api/changes?page=1"

        keep_going = True

        # Ensure we alawys have a timezone-aware datetime
        if since is not None and since.tzinfo is None:
            since = timezone.make_aware(since)

        while keep_going:
            if since:
                url += "&" + urlencode({"since": since.isoformat()})
            try:
                response = client.get(url, headers={"Accept": "application/json"})
                response.raise_for_status()
                entries = response.json()
                for entry in entries:
                    try:
                        ChangeFeedEntry.make(instance=self, entry=entry)
                    except Exception:
                        logger.exception("Failed to parse feed entry", extra={"entry": entry})
                try:
                    url = [
                        st.split(";")[0].removeprefix("<").removesuffix(">")
                        for st in response.headers["link"].split(",")
                        if 'rel="next"' in st
                    ].pop()
                except (IndexError, KeyError):
                    keep_going = False
            except Exception:
                logger.exception(f"Failed to sync change feed from {self}")
                keep_going = False

        self.sync_jobs.create()


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

    @classmethod
    def make(cls, instance, entry):
        change_subclass = {klass.TYPE: klass for klass in cls.__subclasses__()}.get(entry["type"])
        return change_subclass.make(instance, entry)

    class Meta:
        verbose_name_plural = "Change Entries"


class ConnectedRedditAccountEntry(ChangeFeedEntry):
    TYPE = "connection:reddit"
    connection = models.ForeignKey(
        ConnectedRedditAccount, related_name="feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        actor_url = self.connection.actor.url
        return f"{self.connection.reddit_account} connected as {actor_url}"

    @classmethod
    def make(cls, instance, entry):
        reddit_account, _ = RedditAccount.objects.get_or_create(username=entry["reddit_account"])
        actor_url = entry["actor"]
        actor = Person.objects.filter(url=actor_url).first() or Person.fetch(actor_url)

        connection, _ = ConnectedRedditAccount.objects.get_or_create(
            reddit_account=reddit_account, actor=actor
        )
        return cls.objects.create(published_by=instance, connection=connection)


class EndorsementEntry(ChangeFeedEntry):
    TYPE = "endorsement"
    endorsement = models.ForeignKey(
        Endorsement, related_name="feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        return f"{self.endorsement.endorser} endorses {self.endorsement.endorsed}"

    @classmethod
    def make(cls, instance, entry):
        endorsed, _ = FediversedInstance.objects.get_or_create(portal_url=entry["endorsed"])
        endorsement, _ = Endorsement.objects.get_or_create(endorser=instance, endorsed=endorsed)
        return cls.objects.create(published_by=instance, endorsement=endorsement)


class RedditToCommunityRecommendationEntry(ChangeFeedEntry):
    TYPE = "recommendation:group"

    subreddit = models.ForeignKey(
        RedditCommunity, related_name="recommendation_feed_entries", on_delete=models.CASCADE
    )
    community = models.ForeignKey(
        Community, related_name="recommendation_feed_entries", on_delete=models.CASCADE
    )

    @property
    def description(self):
        return f"{self.community} as alternative to {self.subreddit}"

    @classmethod
    def make(cls, instance, entry):
        subreddit_name = entry["subreddit"]
        actor_url = entry["community"]

        assert subreddit_name is not None, "invalid subreddit name"
        assert actor_url is not None, "invalid url for community"

        subreddit = RedditCommunity.objects.filter(
            name__iexact=subreddit_name
        ) or RedditCommunity.fetch(subreddit_name)

        community = Community.objects.filter(url=actor_url).first() or Community.fetch(actor_url)
        return cls.objects.create(published_by=instance, subreddit=subreddit, community=community)


class SyncJob(models.Model):
    run_on = models.DateTimeField(auto_now_add=True)
    instance = models.ForeignKey(
        FediversedInstance, related_name="sync_jobs", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.instance.portal_url} sync run on {self.run_on.isoformat()}"


__all__ = (
    "FediversedInstance",
    "Endorsement",
    "ConnectedRedditAccount",
    "ChangeFeedEntry",
    "EndorsementEntry",
    "ConnectedRedditAccountEntry",
    "RedditToCommunityRecommendationEntry",
    "SyncJob",
)
