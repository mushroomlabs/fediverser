from django.shortcuts import get_object_or_404
from django.views.generic.base import RedirectView, TemplateView

from fediverser.apps.core.models import Instance

from ..settings import app_settings
from .common import SimplePageView


class HomeView(TemplateView):
    @property
    def is_local(self):
        return app_settings.is_local_portal

    def get_template_names(self):
        local = "portal/pages/local/home.tmpl.html"
        network = "portal/pages/network/home.tmpl.html"

        return [local] if self.is_local else [network]


class InstanceFinderView(SimplePageView):
    page_title = "Instance Finder"
    template_name = "portal/pages/network/instance_finder.tmpl.html"
    header_icon = "search"


class InstanceSignupPageView(RedirectView):
    def get_redirect_url(self, *args, **kw):
        instance = get_object_or_404(Instance, domain=self.kwargs["domain"])
        return f"{instance.url}/signup"


__all__ = ("HomeView", "InstanceSignupPageView", "InstanceFinderView")
