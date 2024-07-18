from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from fediverser.apps.core.models import FediversedInstance, Instance
from fediverser.apps.core.models.common import AP_SERVER_SOFTWARE, INSTANCE_STATUSES
from fediverser.apps.core.settings import app_settings
from fediverser.apps.lemmy.services import InstanceProxy
from fediverser.apps.lemmy.settings import app_settings as lemmy_settings

from ..serializers import NodeInfoSerializer

NODE_CONFIGURATION = {
    "portal_url": app_settings.Portal.url,
    "accepts_community_requests": app_settings.Portal.accepts_community_requests,
    "allows_reddit_signup": app_settings.Portal.signup_with_reddit,
    "allows_reddit_mirrored_content": lemmy_settings.Instance.reddit_mirror_bots_enabled,
    "creates_reddit_mirror_bots": app_settings.Reddit.mirroring_enabled,
}


class NodeInfoView(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (JSONRenderer,)

    def get(self, request, *args, **kw):
        lemmy_instance = InstanceProxy.get_connected_instance()

        if lemmy_instance is not None:
            instance, _ = Instance.objects.get_or_create(
                domain=lemmy_instance.domain,
                defaults={
                    "software": AP_SERVER_SOFTWARE.lemmy,
                    "status": INSTANCE_STATUSES.active,
                },
            )
            fediversed_instance, _ = FediversedInstance.objects.update_or_create(
                instance=instance,
                defaults=NODE_CONFIGURATION,
            )
        else:
            fediversed_instance = None

        serializer = NodeInfoSerializer(
            {
                "url": app_settings.Portal.url,
                "registration_methods": app_settings.registration_methods,
                "lemmy": fediversed_instance,
            }
        )
        return Response(serializer.data)


__all__ = ("NodeInfoView",)
