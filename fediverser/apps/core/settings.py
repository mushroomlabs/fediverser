import logging

from django.conf import settings
from django.test.signals import setting_changed

logger = logging.getLogger(__name__)

_SETTINGS_KEY = "FEDIVERSER"


class AppSettings:
    class Hub:
        url = "https://fediverser.network"

    class Portal:
        url = None
        name = "Fediverser Portal"
        open_registrations = True

    class Reddit:
        mirroring_enabled = False
        signup_enabled = True
        bot_username = None
        bot_password = None

    def __init__(self):
        self.load()

    def load(self):
        ATTRS = {
            "PORTAL_URL": (self.Portal, "url"),
            "PORTAL_NAME": (self.Portal, "name"),
            "HUB_URL": (self.Hub, "url"),
            "REDDIT_MIRRORING_ENABLED": (self.Reddit, "mirroring_enabled"),
            "REDDIT_SIGNUP_ENABLED": (self.Reddit, "signup_enabled"),
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
