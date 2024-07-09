from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from allauth.socialaccount.providers.reddit.views import RedditAdapter
from django.http import HttpResponseRedirect
from django.views.generic.base import RedirectView, TemplateView


class HomeView(TemplateView):
    template_name = "portal/pages/home.tmpl.html"


class RedditConnectionView(OAuth2LoginView, RedirectView):
    def get_provider(self):
        return self.adapter.get_provider()

    def dispatch(self, request, *args, **kw):
        self.adapter = RedditAdapter(request)
        provider = self.adapter.get_provider()
        return provider.redirect_from_request(request)

    def get_redirect_url(self, *args, **kw):
        response = self.login(self.request, *args, **kw)
        return response.url
