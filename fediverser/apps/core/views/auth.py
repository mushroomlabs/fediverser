from allauth.socialaccount.providers.base.constants import AuthProcess
from allauth.socialaccount.providers.oauth2.views import OAuth2LoginView
from allauth.socialaccount.providers.reddit.provider import RedditProvider
from allauth.socialaccount.providers.reddit.views import RedditAdapter
from django.urls import reverse
from django.views.generic.base import RedirectView

from fediverser.apps.core.settings import app_settings


class RedditConnectionProvider(RedditProvider):
    def redirect(self, request, process, next_url=None, data=None, **kwargs):
        return super().redirect(request, AuthProcess.CONNECT, next_url=None, data=None, **kwargs)


class FediverserRedditAdapter(RedditAdapter):
    PROVIDER_CLASS = RedditProvider

    def get_provider(self):
        app = self.get_app()
        return self.PROVIDER_CLASS(self.request, app=app)

    def get_app(self):
        return app_settings.reddit_social_application


class FediverserRedditConnectionAdapter(FediverserRedditAdapter):
    PROVIDER_CLASS = RedditConnectionProvider


class RedditLoginView(OAuth2LoginView, RedirectView):
    def get_provider(self):
        return self.adapter.get_provider()

    def dispatch(self, request, *args, **kw):
        self.adapter = FediverserRedditAdapter(request)
        provider = self.adapter.get_provider()
        return provider.redirect_from_request(request)

    def get_redirect_url(self, *args, **kw):
        response = self.login(self.request, *args, **kw)
        return response.url


class RedditConnectionView(OAuth2LoginView, RedirectView):
    def get_provider(self):
        return self.adapter.get_provider()

    def dispatch(self, request, *args, **kw):
        self.adapter = FediverserRedditConnectionAdapter(request)
        provider = self.adapter.get_provider()
        return provider.redirect_from_request(request)

    def get_redirect_url(self, *args, **kw):
        if not self.request.user.is_authenticated:
            return reverse("fediverser-core:reddit-login")

        response = self.login(self.request, *args, **kw)
        return response.url


__all__ = ("RedditLoginView", "RedditConnectionView")
