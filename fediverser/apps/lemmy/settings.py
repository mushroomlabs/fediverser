import logging

from django.conf import settings
from django.test.signals import setting_changed

logger = logging.getLogger(__name__)

_SETTINGS_KEY = "FEDIVERSED_LEMMY"


class AppSettings:
    class Instance:
        domain = None
        reddit_mirror_bots_enabled = False

    class Bot:
        username = None
        password = None

    def __init__(self):
        self.load()

    def load(self):
        ATTRS = {
            "INSTANCE_DOMAIN": (self.Instance, "domain"),
            "REDDIT_MIRROR_BOTS_ENABLED": (self.Instance, "reddit_mirror_bots_enabled"),
            "BOT_USERNAME": (self.Bot, "username"),
            "BOT_PASSWORD": (self.Bot, "password"),
        }
        user_settings = getattr(settings, _SETTINGS_KEY, {})

        for setting, value in user_settings.items():
            if setting not in ATTRS:
                logger.warning(f"Ignoring {setting} as it is not a setting for Fediversed Lemmy")
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
