import logging
from urllib.parse import urlparse

import requests
from allauth.account.forms import PasswordField, SignupForm as BaseSignupForm
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from . import models
from .models.activitypub import AP_SERVER_SOFTWARE
from .models.feeds import CommunityFeed, Feed
from .models.invites import RedditorDeclinedInvite

logger = logging.getLogger(__name__)


class SignupForm(BaseSignupForm):
    def __init__(self, *args, **kw):
        super(SignupForm, self).__init__(*args, **kw)
        self.fields["password1"] = PasswordField(
            label=_("Password"), autocomplete="new-password", help_text=""
        )


class ContentFeedField(forms.Field):
    def to_python(self, value):
        if not value:
            return None
        return Feed.make(value)


class CategoryPickerForm(forms.Form):
    category = forms.ModelChoiceField(queryset=models.Category.objects.all())


class SubredditCreateForm(forms.ModelForm):
    def save(self):
        name = self.cleaned_data["name"]
        try:
            return models.RedditCommunity.fetch(name)
        except Exception as exc:
            raise ValidationError(f"Could not verify details for {name} subreddit: {exc}")

    class Meta:
        model = models.RedditCommunity
        fields = ("name",)


class CommunityCreateForm(forms.ModelForm):
    url = forms.URLField(
        required=True, help_text="Full URL of community (e.g, https://lemmy.ml/c/fediverse)"
    )

    @property
    def community_data(self):
        if not hasattr(self, "_community_data"):
            self._community_data = models.Community.get_metadata(self.cleaned_data["url"])
        return self._community_data

    @property
    def instance_info(self):
        if not hasattr(self, "_instance_info"):
            self._instance_info = models.Instance.get_software_info(self.cleaned_data["url"])
        return self._instance_info

    def _find_by_url(self, url):
        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        community_name = parsed_url.path.split("/")[-1].lower()

        return models.Community.objects.filter(
            instance__domain=domain, name=community_name
        ).first()

    def clean(self):
        cleaned_data = super(CommunityCreateForm, self).clean()
        url = cleaned_data["url"]
        try:
            server_type = self.instance_info["software"]["name"]
            assert self._find_by_url(url) is None, f"{url} is already in the database"
            assert (
                server_type in AP_SERVER_SOFTWARE
            ), "We do not support {server_type} servers, yet."

            assert self.community_data is not None, "could not get community details"
        except KeyError as exc:
            logger.exception(exc)
            raise ValidationError("This does not seem to be a Fediverse-compatible server")
        except AssertionError as exc:
            raise ValidationError(str(exc))
        except requests.HTTPError as exc:
            logger.exception(exc)
            raise ValidationError("Invalid server, server offline or community does not exist")

    def save(self, *args, **kw):
        url = self.cleaned_data["url"]
        return models.Community.fetch(url)

    class Meta:
        model = models.Community
        fields = ("url",)


class InstanceCreateForm(forms.ModelForm):
    url = forms.URLField(required=True, help_text="Full URL of instance (e.g, https://lemmy.ml)")

    @property
    def server_software(self):
        return self.instance_info["software"]["name"]

    @property
    def instance_info(self):
        if not hasattr(self, "_instance_info"):
            self._instance_info = models.Instance.get_software_info(self.cleaned_data["url"])
        return self._instance_info

    def clean(self):
        try:
            assert (
                self.server_software in AP_SERVER_SOFTWARE
            ), f"We are not tracking {self.server_software} instances yet"
        except AssertionError as exc:
            raise ValidationError(str(exc))
        except requests.HTTPError:
            raise ValidationError("Invalid server or server offline")
        except KeyError:
            raise ValidationError("Server can not be identified as ActivityPub-compatible")

    def save(self, *args, **kw):
        url = self.cleaned_data["url"]
        parsed_url = urlparse(url)
        domain = parsed_url.hostname
        instance, _ = models.Instance.objects.get_or_create(
            domain=domain, defaults={"software": self.server_software}
        )
        return instance

    class Meta:
        model = models.Instance
        fields = ("url",)


class SubredditAlternativeRecommendationForm(CommunityCreateForm):
    def clean(self):
        url = self.cleaned_data["url"]
        if self._find_by_url(url) is not None:
            return

        super().clean()

    def save(self, *args, **kw):
        url = self.cleaned_data["url"]
        community = self._find_by_url(url) or super().save(*args, **kw)
        self.instance.community = community
        self.instance.save()
        return self.instance

    class Meta:
        model = models.RecommendCommunity
        fields = ("url",)


class CommunityRequestForm(forms.ModelForm):
    instance = forms.ModelChoiceField(
        queryset=models.Instance.objects.filter(
            fediverser_configuration__accepts_community_requests=True
        )
    )

    class Meta:
        model = models.CommunityRequest
        fields = ("instance",)


class CommunityCategoryRecommendationForm(forms.ModelForm):
    class Meta:
        model = models.SetCommunityCategory
        fields = ("category",)


class SubredditCategoryRecommendationForm(forms.ModelForm):
    class Meta:
        model = models.SetRedditCommunityCategory
        fields = ("category",)


class InstanceCategoryRecommendationForm(forms.ModelForm):
    class Meta:
        model = models.SetInstanceCategory
        fields = ("category",)


class InstanceCountryRecommendationForm(forms.ModelForm):
    country = CountryField().formfield()

    class Meta:
        model = models.SetInstanceCountry
        fields = ("country",)


class CommunityFeedForm(forms.ModelForm):
    feed = ContentFeedField()

    class Meta:
        model = CommunityFeed
        fields = ("feed",)


class RedditorDeclinedInviteForm(forms.ModelForm):
    class Meta:
        model = RedditorDeclinedInvite
        fields = ("reason", "note")
