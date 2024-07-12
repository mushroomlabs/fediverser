import logging
from urllib.parse import urlparse

import cloudscraper
from django.db import models
from pythorhead.types import LanguageType
from taggit.managers import TaggableManager

from fediverser.apps.lemmy.models import Community as LemmyCommunity, Language
from fediverser.apps.lemmy.services import InstanceProxy

from .common import AP_SERVER_SOFTWARE, INSTANCE_STATUSES, Category

logger = logging.getLogger(__name__)


AP_CLIENT_REQUEST_HEADERS = {"Accept": "application/ld+json"}


def make_ap_client():
    scraper = cloudscraper.create_scraper(
        browser={"browser": "firefox", "platform": "linux", "mobile": False}
    )
    scraper.headers.update(**AP_CLIENT_REQUEST_HEADERS)
    return scraper


class Instance(models.Model):
    domain = models.CharField(max_length=255, unique=True)
    category = models.ForeignKey(
        Category,
        related_name="instances",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(max_length=20, choices=INSTANCE_STATUSES, null=True, blank=True)
    name = models.CharField(max_length=30, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    over18 = models.BooleanField(default=False)
    open_registrations = models.BooleanField(default=False)
    tags = TaggableManager(blank=True)
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
        full_url = f"https://{domain}/nodeinfo/2.0.json"
        scraper = make_ap_client()
        response = scraper.get(full_url)
        response.raise_for_status()
        return response.json()

    def __str__(self):
        return self.domain


class FediversedInstance(models.Model):
    instance = models.OneToOneField(
        Instance, related_name="fediverser_configuration", on_delete=models.CASCADE
    )
    allows_reddit_signup = models.BooleanField(default=True)
    allows_reddit_mirrored_content = models.BooleanField(default=False)
    accepts_community_requests = models.BooleanField(
        default=False, help_text="Accepts Community Requests"
    )


class Community(models.Model):
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
    tags = TaggableManager(blank=True)

    @property
    def fqdn(self):
        return f"{self.name}@{self.instance.domain}"

    @property
    def url(self):
        return f"https://{self.instance.domain}/c/{self.name}"

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
    def get_metadata(cls, url):
        scraper = make_ap_client()
        response = scraper.get(url)
        response.raise_for_status()

        return response.json()

    class Meta:
        unique_together = ("instance", "name")
        verbose_name_plural = "Communities"


__all__ = ("Instance", "Community")
