import logging

import environ
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.reddit.provider import RedditProvider
from django.conf import settings

logger = logging.getLogger(__name__)
env = environ.Env()
environ.Env.read_env()


class AppSettings:
    class Portal:
        url = env.str("FEDIVERSER_PORTAL_URL", default=None)
        name = settings.SITE_NAME
        open_registrations = env.bool("FEDIVERSER_PORTAL_OPEN_REGISTRATIONS", default=False)
        hub_url = env.str("FEDIVERSER_HUB_URL", default="https://fediverser.network")
        signup_with_reddit = env.bool("FEDIVERSER_ENABLE_REDDIT_SIGNUP", default=True)
        global_lemmy_instance_selector = env.bool(
            "FEDIVERSER_GLOBAL_LEMMY_INSTANCE_LOCATOR", default=False
        )
        accepts_community_requests = env.bool(
            "FEDIVERSER_ENABLE_ANONYMOUS_COMMUNITY_REQUESTS", default=False
        )

    class Reddit:
        mirroring_enabled = False
        bot_username = None
        bot_password = None

    @property
    def registration_methods(self):
        methods = []
        if self.Portal.open_registrations:
            methods.append("direct")

        if self.Portal.signup_with_reddit:
            methods.append("reddit")

        return methods

    @property
    def oauth_reddit_application_name(self):
        return f"Login with Reddit on {self.Portal.name}"

    @property
    def reddit_social_application(self):
        app, _ = SocialApp.objects.get_or_create(
            client_id=settings.REDDIT_CLIENT_ID,
            defaults={
                "provider": RedditProvider.id,
                "name": app_settings.oauth_reddit_application_name,
                "secret": settings.REDDIT_CLIENT_SECRET,
            },
        )
        return app

    @property
    def provides_automatic_lemmy_onboarding(self):
        return settings.FEDIVERSER_ENABLE_LEMMY_INTEGRATION

    @property
    def is_local_portal(self):
        return self.provides_automatic_lemmy_onboarding

    @property
    def is_network_portal(self):
        return not self.is_local_portal


app_settings = AppSettings()
