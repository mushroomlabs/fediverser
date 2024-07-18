from rest_framework import generics
from rest_framework.permissions import AllowAny

from fediverser.apps.core.models import FediversedInstance

from ..filters import FediversedInstanceFilter
from ..serializers import FediversedInstanceSerializer


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


__all__ = ("NodeInfoView", "FediversedInstanceListView")
