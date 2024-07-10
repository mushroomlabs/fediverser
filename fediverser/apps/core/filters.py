from django_filters import rest_framework as filters

from . import models


class ChangeRequestFilter(filters.FilterSet):
    class Meta:
        model = models.ChangeRequest
        fields = ("status",)


class InstanceFilter(filters.FilterSet):
    class Meta:
        model = models.Instance
        fields = ("category", "software")


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
