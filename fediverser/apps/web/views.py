from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from allauth.socialaccount.providers.reddit.views import RedditAdapter
from django.views.generic.base import RedirectView, TemplateView


class HomeView(TemplateView):
    template_name = "web/home.tmpl.html"


class RedditConnectionView(RedirectView, OAuth2LoginView):
    def get_redirect_url(self, *args, **kw):
        self.adapter = RedditAdapter(self.request)
        response = self.login(self.request, *args, **kw)
        return response.url
