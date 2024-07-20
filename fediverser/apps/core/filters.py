from django.db.models import Q
from django_countries import countries
from django_filters import rest_framework as filters

from . import models


def get_country_list():
    country_list = models.InstanceCountry.objects.values_list("country", flat=True).distinct()
    return [(c, countries.name(c)) for c in country_list]


class ChangeRequestFilter(filters.FilterSet):
    class Meta:
        model = models.ChangeRequest
        fields = ("status",)


class InstanceFilter(filters.FilterSet):
    country = filters.ChoiceFilter(choices=get_country_list, label="Country", method="by_country")

    def by_country(self, queryset, name, value):
        return queryset.filter(related_countries__country=value)

    class Meta:
        model = models.Instance
        fields = ("category", "software", "country")


class CommunityFilter(filters.FilterSet):
    instance__domain = filters.CharFilter(label="By Instance domain", lookup_expr="icontains")
    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = models.Community
        fields = ("name", "category")


class RedditCommunityFilter(filters.FilterSet):
    search = filters.CharFilter(label="search", field_name="name", lookup_expr="icontains")
    mapped = filters.BooleanFilter(label="mapped", method="with_recommendations")
    subscribed = filters.BooleanFilter(label="subscribed", method="with_reddit_subscriptions")

    def with_recommendations(self, queryset, name, value):
        return queryset.exclude(recommendations__isnull=value)

    def with_reddit_subscriptions(self, queryset, name, value):
        action = queryset.filter if value else queryset.exclude
        return action(subscribers=self.request.user)

    class Meta:
        model = models.RedditCommunity
        fields = (
            "name",
            "subscribed",
            "mapped",
            "category",
            "over18",
            "locked",
        )


class ChangeFeedFilter(filters.FilterSet):
    since = filters.DateTimeFilter(label="since", field_name="created", lookup_expr="gte")
    until = filters.DateTimeFilter(label="until", field_name="created", lookup_expr="lte")

    class Meta:
        model = models.ChangeFeedEntry
        fields = ("since", "until")


class FediversedInstanceFilter(filters.FilterSet):
    search = filters.CharFilter(label="search", method="instance_search")
    trusted = filters.BooleanFilter(label="trusted", method="trusted_by_us")

    def instance_search(self, queryset, name, value):
        instance_domain_q = Q(instance__domain__icontains=value)
        portal_q = Q(portal_url__icontains=value)
        return queryset.filter(instance_domain_q | portal_q)

    def trusted_by_us(self, queryset, name, value):
        action = queryset.filter if value else queryset.exclude
        us = models.FediversedInstance.current()
        return action(endorsed_instances__endorser=us)

    class Meta:
        model = models.FediversedInstance
        fields = (
            "search",
            "trusted",
            "accepts_community_requests",
            "allows_reddit_mirrored_content",
            "allows_reddit_signup",
            "creates_reddit_mirror_bots",
        )
