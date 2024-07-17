from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from allauth.socialaccount.providers.reddit.provider import RedditProvider
from allauth.socialaccount.providers.reddit.views import RedditAdapter
from django.views.generic.base import RedirectView

from fediverser.apps.core.settings import app_settings


class FediverserRedditAdapter(RedditAdapter):
    def get_provider(self):
        app = self.get_app()
        return RedditProvider(self.request, app=app)

    def get_app(self):
        return app_settings.reddit_social_application


class RedditConnectionView(OAuth2LoginView, RedirectView):
    def get_provider(self):
        return self.adapter.get_provider()

    def dispatch(self, request, *args, **kw):
        self.adapter = FediverserRedditAdapter(request)
        provider = self.adapter.get_provider()
        return provider.redirect_from_request(request)

    def get_redirect_url(self, *args, **kw):
        response = self.login(self.request, *args, **kw)
        return response.url
