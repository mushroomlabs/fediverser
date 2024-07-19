from django.urls import reverse
from django.views.generic.base import RedirectView
from rest_framework import generics
from rest_framework.permissions import AllowAny

from fediverser.apps.core.models import FediversedInstance

from ..filters import FediversedInstanceFilter
from ..serializers import FediversedInstanceSerializer
from ..settings import app_settings


class NodeInfoView(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FediversedInstanceSerializer

    def get_object(self, *args, **kw):
        return FediversedInstance.current()


class FediversedInstanceListView(generics.ListCreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = FediversedInstanceSerializer
    filterset_class = FediversedInstanceFilter

    def get_queryset(self):
        return FediversedInstance.objects.all()


class SelectLemmyInstanceView(RedirectView):
    def get_redirect_url(self):
        if app_settings.is_local_portal:
            return reverse("fediverser-core:reddit-connection-setup")

        instance = self.request.user.account.get_recommended_portal()
        return f"{instance.portal_url}/connect/reddit"


__all__ = ("NodeInfoView", "FediversedInstanceListView", "SelectLemmyInstanceView")
