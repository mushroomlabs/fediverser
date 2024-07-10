from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse

from ..models.accounts import CommunityAmbassadorApplication
from ..models.activitypub import Community
from .common import CreateView


class CommunityAmbassadorApplicationCreateView(CreateView):
    model = CommunityAmbassadorApplication
    page_title = "Community Ambassador"
    view_name = "fediverser-core:community-ambassador-application-create"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:community-detail", kwargs=self.kwargs)

    def post(self, request, *args, **kw):
        community = get_object_or_404(
            Community, name=self.kwargs["name"], instance__domain=self.kwargs["instance_domain"]
        )
        self.model.objects.update_or_create(requester=request.user, community=community)
        return HttpResponseRedirect(self.get_success_url())


__all__ = ("CommunityAmbassadorApplicationCreateView",)
