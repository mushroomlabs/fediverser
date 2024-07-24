from django.db.models import Case, Exists, F, FloatField, OuterRef, Q, When
from django_countries import countries
from django_filters import rest_framework as filters

from . import models


def get_country_list():
    country_list = models.InstanceCountry.objects.values_list("country", flat=True).distinct()
    return [(c, countries.name(c)) for c in country_list]


def get_topic_list():
    return [(d.code, d.name) for d in models.Topic.objects.all()]


class ChangeRequestFilter(filters.FilterSet):
    class Meta:
        model = models.ChangeRequest
        fields = ("status",)


class InstanceFilter(filters.FilterSet):
    country = filters.ChoiceFilter(choices=get_country_list, label="Country", method="by_country")
    topic = filters.ChoiceFilter(choices=get_topic_list, label="Interests", method="by_topic")

    def by_country(self, queryset, name, value):
        return queryset.filter(related_countries__country=value)

    def by_topic(self, queryset, name, value):
        return queryset.filter(topics__topic__code=value)

    class Meta:
        model = models.Instance
        fields = ("software", "country", "topic")


class InstanceRecommendationFilter(InstanceFilter):
    topic = filters.MultipleChoiceFilter(
        choices=get_topic_list, label="Interests", method="by_topic"
    )

    def get_annotated_score(self, queryset, conditional, weight=2):
        when_exists = When(Exists(conditional), then=weight * F("score"))
        when_not_exists = When(~Exists(conditional), then=F("score") / weight)
        return queryset.annotate(
            score=Case(when_exists, when_not_exists, default=F("score"), output_field=FloatField())
        )

    def by_country(self, queryset, name, value):
        return self.get_annotated_score(
            queryset,
            models.InstanceCountry.objects.filter(instance=OuterRef("pk"), country=value),
            weight=10,
        )

    def by_topic(self, queryset, name, value):
        return self.get_annotated_score(
            queryset,
            models.InstanceTopic.objects.filter(instance=OuterRef("pk"), topic__code__in=value),
        )

    @property
    def qs(self):
        queryset = super().qs
        if "topic" not in self.data:
            queryset = self.get_annotated_score(
                queryset, models.InstanceTopic.objects.filter(instance=OuterRef("pk")), weight=0.5
            )
        return queryset

    class Meta:
        model = models.Instance
        fields = ("country", "topic")


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
        return action(useraccount__user=self.request.user)

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
