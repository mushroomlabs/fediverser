from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic.base import TemplateView

from fediverser.apps.core.models import Person
from fediverser.apps.lemmy.forms import (
    SetPasswordForm as LemmySetPasswordForm,
    SignupForm as LemmySignupForm,
)

from ..settings import app_settings
from ..signals import redditor_migrated
from .common import FormView, SimplePageView


class HomeView(TemplateView):
    @property
    def is_local(self):
        return app_settings.is_local_portal

    def get_template_names(self):
        local = "portal/pages/local/home.tmpl.html"
        network = "portal/pages/network/home.tmpl.html"

        return [local] if self.is_local else [network]


class LemmySignupView(FormView):
    page_title = "Signup"
    header_icon = "register"
    form_class = LemmySignupForm
    view_name = "fediverser-core:lemmy-connect-setup"
    template_name = "portal/instance/signup.tmpl.html"
    success_url = reverse_lazy("fediverser-core:portal-home")

    def form_valid(self, form):
        username = form.cleaned_data["username"]
        local_user = form.signup()
        messages.success(self.request, f"Username {username} created")
        person = Person.make_from_lemmy_local_user(local_user)
        self.request.user.account.lemmy_local_username = username
        self.request.user.account.save()

        for social_account in self.request.user.socialaccount_set.filter(provider="reddit"):
            try:
                redditor_migrated.send(
                    sender=Person,
                    reddit_username=social_account.extra_data["name"],
                    activitypub_actor=person,
                )
            except KeyError:
                pass
        return super().form_valid(form)


class LemmySetPasswordView(FormView):
    page_title = "Set Lemmy Account Password"
    header_icon = "lock"
    form_class = LemmySetPasswordForm
    view_name = "fediverser-core:lemmy-set-password"
    success_url = reverse_lazy("fediverser-core:portal-home")

    def form_valid(self, form):
        local_user = self.request.user.account.lemmy_local_user
        local_user.set_password(form.cleaned_data["password1"])
        messages.success(self.request, f"Password for {local_user} set")
        return super().form_valid(form)


class InstanceFinderView(SimplePageView):
    page_title = "Instance Finder"
    template_name = "portal/pages/network/instance_finder.tmpl.html"
    header_icon = "search"


__all__ = (
    "HomeView",
    "LemmySignupView",
    "LemmySetPasswordView",
    "InstanceFinderView",
)
