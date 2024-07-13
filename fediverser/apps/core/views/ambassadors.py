import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic.base import RedirectView

from fediverser.apps.lemmy.services import CommunityProxy

from ..models.accounts import CommunityAmbassadorApplication
from ..models.activitypub import Community
from ..models.mirroring import LemmyMirroredPost
from ..models.reddit import RedditSubmission
from .common import CreateView

logger = logging.getLogger(__name__)


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


class CommunityRepostRedditSubmissionView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kw):
        community = get_object_or_404(
            Community,
            name=self.kwargs["name"],
            instance__domain=self.kwargs["instance_domain"],
        )
        lemmy_community = CommunityProxy.objects.get_by_fqdn(community.fqdn)
        create_post_url = f"https://{lemmy_community.instance.domain}/create_post"
        original_url = self.request.GET.get("url")
        reddit_submission = get_object_or_404(RedditSubmission, url=original_url)
        lemmy_client = self.request.user.account.lemmy_client
        try:
            post_payload = LemmyMirroredPost.prepare_lemmy_post_from_reddit_submission(
                lemmy_client, reddit_submission, community
            )
        except Exception as exc:
            logger.warning(f"Failed to prepare post for {original_url}: {exc}")
            post_payload = {"url": original_url}

        query_string = LemmyMirroredPost.lemmy_post_payload_to_query_string(post_payload)
        return f"{create_post_url}?{query_string}"


__all__ = ("CommunityAmbassadorApplicationCreateView", "CommunityRepostRedditSubmissionView")
