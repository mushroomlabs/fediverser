import logging

import environ
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.reddit.provider import RedditProvider
from django.conf import settings
from django.test.signals import setting_changed

logger = logging.getLogger(__name__)
env = environ.Env()
environ.Env.read_env()

_SETTINGS_KEY = "FEDIVERSER"


class AppSettings:
    class Portal:
        url = None
        name = "Fediverser Portal"
        open_registrations = env.bool("FEDIVERSER_PORTAL_OPEN_REGISTRATIONS", default=False)
        default_hub_url = "https://fediverser.network"
        signup_with_reddit = True
        global_lemmy_instance_selector = False
        accepts_community_requests = False

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

    def __init__(self):
        self.load()

    def load(self):
        ATTRS = {
            "URL": (self.Portal, "url"),
            "NAME": (self.Portal, "name"),
            "HUB_URL": (self.Portal, "default_hub_url"),
            "ACCEPTS_COMMUNITY_REQUESTS": (self.Portal, "accepts_community_requests"),
            "GLOBAL_LEMMY_INSTANCE_LOCATOR": (self.Portal, "global_lemmy_instance_selector"),
            "REDDIT_SIGNUP_ENABLED": (self.Portal, "signup_with_reddit"),
            "REDDIT_MIRRORING_ENABLED": (self.Reddit, "mirroring_enabled"),
            "REDDIT_BOT_USERNAME": (self.Reddit, "bot_username"),
            "REDDIT_BOT_PASSWORD": (self.Reddit, "bot_password"),
        }
        user_settings = getattr(settings, _SETTINGS_KEY, {})

        for setting, value in user_settings.items():
            logger.debug(f"setting {setting} -> {value}")
            if setting not in ATTRS:
                logger.warning(f"Ignoring {setting} as it is not a setting for ActivityPub")
                continue

            setting_class, attr = ATTRS[setting]
            setattr(setting_class, attr, value)


app_settings = AppSettings()


def reload_settings(*args, **kw):
    global app_settings
    setting = kw["setting"]
    if setting == _SETTINGS_KEY:
        app_settings.load()


setting_changed.connect(reload_settings)
