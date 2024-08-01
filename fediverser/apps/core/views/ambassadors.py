import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic.base import RedirectView
from invitations.adapters import get_invitations_adapter
from invitations.app_settings import app_settings as invitations_settings
from invitations.views import AcceptInvite

from ..forms import RedditorDeclinedInviteForm
from ..models.accounts import CommunityAmbassadorApplication
from ..models.activitypub import Community
from ..models.invites import RedditorInvite
from ..models.mirroring import LemmyMirroredPost
from ..models.reddit import RedditAccount, RedditSubmission
from .common import AnonymousSurveyView, CreateView

logger = logging.getLogger(__name__)


class RedditorAcceptInviteView(AcceptInvite):

    def get(self, *args, **kw):
        if self.request.user.is_authenticated:
            logout(self.request)
        self.object = invite = self.get_object()
        return render(self.request, "portal/home/invite.tmpl.html", {"invite": invite})

    def post(self, *args, **kw):
        self.object = invite = self.get_object()

        # No invite was found.
        if not invite:
            # Newer behavior: show an error message and redirect.
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                "invitations/messages/invite_invalid.txt",
            )
            return redirect(invitations_settings.LOGIN_REDIRECT)

        # The invite was previously accepted, redirect to the login
        # view.
        if invite.accepted:
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                "invites/already_accepted.tmpl.txt",
                {"redditor": invite.redditor},
            )
            # Redirect to login since there's hopefully an account already.
            return redirect(invitations_settings.LOGIN_REDIRECT)

        # The key was expired.
        if invite.key_expired():
            get_invitations_adapter().add_message(
                self.request,
                messages.ERROR,
                "invites/expired.tmpl.txt",
                {"redditor": invite.redditor},
            )
            # Redirect to sign-up since they might be able to register anyway.
            return redirect(self.get_signup_redirect())

        # The invite is valid.
        invite.accepted = True
        invite.save()
        return redirect(reverse("fediverser-core:reddit-login"))

    def get_queryset(self):
        return RedditorInvite.objects.all()


class RedditorDeclineInviteView(AnonymousSurveyView):
    form_class = RedditorDeclinedInviteForm
    page_title = "Decline Invite"
    template_name = "portal/redditor/decline_invite.tmpl.html"

    @property
    def action_url(self):
        invite = self.get_invite()
        return reverse("fediverser-core:redditor-decline-invite", kwargs={"key": invite.key})

    def get_invite(self):
        return get_object_or_404(RedditorInvite, key=self.kwargs["key"])

    def get_success_url(self, *args, **kw):
        invite = self.get_invite()
        return reverse(
            "fediverser-core:redditor-detail", kwargs={"username": invite.redditor.username}
        )

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        context.update({"invite": self.get_invite()})
        return context

    def form_valid(self, form):
        invite = self.get_invite()

        form.instance.redditor = invite.redditor
        form.instance.key = invite.key
        form.save()

        messages.info(
            self.request,
            "Your invite declination was recorded. No DMs will be sent to you on Reddit",
        )
        return HttpResponseRedirect(self.get_success_url())


class RedditorInviteView(CreateView):
    model = RedditorInvite
    page_title = "Invite Redditor"
    view_name = "fediverser-core:redditor-send-invite"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:redditor-detail", kwargs=self.kwargs)

    def post(self, request, *args, **kw):
        redditor = get_object_or_404(RedditAccount, **self.kwargs)

        RedditorInvite.create(redditor=redditor, inviter=self.request.user)
        return HttpResponseRedirect(self.get_success_url())


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
    def get(self, *args, **kw):
        lemmy_client = self.request.user.account.lemmy_client
        if lemmy_client is None:
            return HttpResponse("User is not connected to any Lemmy account", status=421)

        return super().get(*args, **kw)

    def get_redirect_url(self, *args, **kw):
        community = get_object_or_404(
            Community,
            name=self.kwargs["name"],
            instance__domain=self.kwargs["instance_domain"],
        )
        lemmy_client = self.request.user.account.lemmy_client
        original_url = self.request.GET.get("url")
        reddit_submission = get_object_or_404(RedditSubmission, url=original_url)
        try:
            post_payload = LemmyMirroredPost.prepare_lemmy_post_from_reddit_submission(
                lemmy_client, reddit_submission, community
            )
        except Exception as exc:
            logger.warning(f"Failed to prepare post for {original_url}: {exc}")
            post_payload = {"url": original_url}

        query_string = LemmyMirroredPost.lemmy_post_payload_to_query_string(post_payload)
        create_post_url = f"https://{lemmy_client._requestor.domain}/create_post"
        return f"{create_post_url}?{query_string}"


__all__ = (
    "CommunityAmbassadorApplicationCreateView",
    "CommunityRepostRedditSubmissionView",
    "RedditorAcceptInviteView",
    "RedditorDeclineInviteView",
    "RedditorInviteView",
)
