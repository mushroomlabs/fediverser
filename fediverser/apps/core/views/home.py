from django.views.generic.base import TemplateView

from ..settings import app_settings


class HomeView(TemplateView):
    def get_template_names(self):
        local = "portal/pages/local/home.tmpl.html"
        network = "portal/pages/network/home.tmpl.html"

        return [local] if app_settings.is_local_portal else [network]
