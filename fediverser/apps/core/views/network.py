from django.contrib.syndication.views import Feed
from django.http import Http404
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from rest_framework import generics
from rest_framework.permissions import AllowAny

from fediverser.apps.core.models import ChangeFeedEntry, FediversedInstance

from .. import serializers
from ..filters import ChangeFeedFilter, FediversedInstanceFilter
from ..settings import app_settings


class NodeInfoView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.FediversedInstanceSerializer

    def get_object(self, *args, **kw):
        return FediversedInstance.current()


class FediversedInstanceListView(generics.ListCreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.FediversedInstanceSerializer
    filterset_class = FediversedInstanceFilter

    def get_queryset(self):
        return FediversedInstance.objects.all()


class ChangeFeedEntryListView(generics.ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PolymorphicChangeFeedEntrySerializer
    filterset_class = ChangeFeedFilter

    def get_queryset(self):
        return ChangeFeedEntry.objects.filter(
            published_by__portal_url=app_settings.Portal.url
        ).select_subclasses()


class ChangeFeedEntryDetailView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PolymorphicChangeFeedEntrySerializer

    def get_object(self):
        try:
            self.object = ChangeFeedEntry.objects.filter(
                published_by__portal_url=app_settings.Portal.url
            ).get_subclass(id=self.kwargs["pk"])
            return self.object
        except ChangeFeedEntry.DoesNotExist:
            raise Http404


class ChangeFeed(Feed):
    feed_type = Atom1Feed
    title = "Change Feed Stream"
    link = "/changes/feed"
    description = "Stream of changes done to internal dataset"

    def items(self):
        return ChangeFeedEntry.objects.select_subclasses().order_by("-modified")[:100]

    def item_title(self, item):
        return item.description

    def item_pubdate(self, item):
        return item.created

    def item_description(self, item):
        return item.description

    def item_link(self, item):
        return reverse("fediverser-core:changefeedentry-detail", args=[item.pk])


__all__ = (
    "NodeInfoView",
    "FediversedInstanceListView",
    "ChangeFeedEntryListView",
    "ChangeFeedEntryDetailView",
    "ChangeFeed",
)
