import logging
from urllib.parse import urlparse

from django.db import models
from pythorhead.types import LanguageType

from fediverser.apps.lemmy.models import Community as LemmyCommunity, Language
from fediverser.apps.lemmy.services import InstanceProxy

from .common import AP_SERVER_SOFTWARE, Category, make_http_client

logger = logging.getLogger(__name__)


AP_CLIENT_REQUEST_HEADERS = {"Accept": "application/ld+json;application/activity+json"}


def make_ap_client():
    client = make_http_client()
    client.headers.update(**AP_CLIENT_REQUEST_HEADERS)
    return client


class Instance(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=30, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    over18 = models.BooleanField(default=False)
    open_registrations = models.BooleanField(default=False)
    software = models.CharField(max_length=30, choices=AP_SERVER_SOFTWARE)

    @property
    def url(self):
        return f"https://{self.domain}"

    @property
    def mirroring(self):
        return InstanceProxy.objects.filter(domain=self.domain).first()

    def natural_key(self):
        return self.domain

    @classmethod
    def get_software_info(cls, url):
        domain = urlparse(url).hostname
        scraper = make_ap_client()

        nodeinfo_url = f"https://{domain}/.well-known/nodeinfo"
        nodeinfo_response = scraper.get(nodeinfo_url)
        nodeinfo_response.raise_for_status()
        nodeinfo_data = nodeinfo_response.json()

        full_url = nodeinfo_data["links"][0]["href"]
        response = scraper.get(full_url)
        response.raise_for_status()
        return response.json()

    @classmethod
    def fetch(cls, url):
        domain = urlparse(url).hostname
        software_info = cls.get_software_info(url)

        instance, _ = cls.objects.update_or_create(
            domain=domain,
            defaults={
                "software": software_info["software"]["name"],
                "open_registrations": software_info.get("openRegistrations") or False,
            },
        )
        return instance

    def __str__(self):
        return self.domain


class ActorMixin:
    instance = models.ForeignKey(Instance, on_delete=models.CASCADE)

    @property
    def fqdn(self):
        return f"{self.name}@{self.instance.domain}"

    @classmethod
    def get_metadata(cls, url):
        scraper = make_ap_client()
        response = scraper.get(url)
        response.raise_for_status()

        return response.json()


class Community(models.Model, ActorMixin):
    instance = models.ForeignKey(Instance, related_name="communities", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    category = models.ForeignKey(
        Category,
        related_name="communities",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    url = models.URLField(unique=True)

    @property
    def languages(self):
        return [
            LanguageType(language_id)
            for language_id in (
                Language.objects.filter(
                    communitylanguage__community__name=self.name,
                    communitylanguage__community__instance__domain=self.instance.domain,
                ).values_list("id", flat=True)
            )
        ]

    @property
    def mirroring(self):
        if self.instance.mirroring is None:
            return None

        return LemmyCommunity.objects.filter(
            instance=self.instance.mirroring, name=self.name
        ).first()

    def __str__(self):
        return self.fqdn

    @classmethod
    def fetch(cls, url):
        try:
            domain = urlparse(url).hostname
            instance = Instance.objects.filter(domain=domain).first() or Instance.fetch(
                f"https://{domain}"
            )
            client = make_ap_client()
            response = client.get(url)
            response.raise_for_status()
            community_data = response.json()

            assert community_data.get("type") == "Group", "not an AP Group actor"
            name = community_data["preferredUsername"]
            community, _ = cls.objects.get_or_create(
                url=url, defaults={"instance": instance, "name": name}
            )
            return community
        except (KeyError, AssertionError) as exc:
            raise ValueError(str(exc))

    class Meta:
        unique_together = ("instance", "name")
        verbose_name_plural = "Communities"


class Person(models.Model, ActorMixin):
    instance = models.ForeignKey(Instance, related_name="users", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    url = models.URLField(unique=True)

    @classmethod
    def fetch(cls, url):
        try:
            domain = urlparse(url).hostname
            instance = Instance.objects.filter(domain=domain).first() or Instance.fetch(
                f"https://{domain}"
            )
            client = make_ap_client()
            response = client.get(url)
            response.raise_for_status()
            person_data = response.json()

            assert person_data.get("type") == "Person", "not an AP Person actor"
            name = person_data["preferredUsername"]
            person, _ = cls.objects.update_or_create(
                url=url, defaults={"instance": instance, "name": name}
            )
            return person
        except (KeyError, AssertionError) as exc:
            raise ValueError(str(exc))


__all__ = ("Instance", "Community", "Person")
