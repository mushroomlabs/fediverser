from django.contrib.syndication.views import Feed
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.feedgenerator import Atom1Feed
from django.views.generic.base import RedirectView
from rest_framework import generics
from rest_framework.permissions import AllowAny

from fediverser.apps.core.models import ChangeFeedEntry, FediversedInstance, Instance

from .. import serializers
from ..filters import ChangeFeedFilter, FediversedInstanceFilter
from ..settings import app_settings


class SelectLemmyInstanceView(RedirectView):
    def get_redirect_url(self):
        if app_settings.is_local_portal:
            return reverse("fediverser-core:reddit-connection-setup")

        instance = self.request.user.account.get_recommended_portal()
        return f"{instance.portal_url}/connect/reddit"


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


class InstanceSignupPageView(RedirectView):
    def get_redirect_url(self, *args, **kw):
        instance = get_object_or_404(Instance, domain=self.kwargs["domain"])
        return f"{instance.url}/signup"


__all__ = (
    "NodeInfoView",
    "FediversedInstanceListView",
    "SelectLemmyInstanceView",
    "ChangeFeedEntryListView",
    "ChangeFeedEntryDetailView",
    "ChangeFeed",
    "InstanceSignupPageView",
)
