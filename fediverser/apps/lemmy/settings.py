import logging

import environ

logger = logging.getLogger(__name__)
env = environ.Env()
environ.Env.read_env()


class AppSettings:
    class Instance:
        domain = env.str("FEDIVERSER_CONNECTED_LEMMY_INSTANCE", default=None)
        reddit_mirror_bots_enabled = env.bool("REDDIT_MIRROR_BOTS_ENABLED", default=False)

    class Bot:
        username = env.str("FEDIVERSER_BOT_USERNAME", default=None)
        password = env.str("FEDIVERSER_BOT_PASSWORD", default=None)

    @property
    def integration_enabled(self):
        enabled = env.bool("FEDIVERSER_ENABLE_LEMMY", default=True)
        return enabled and self.Instance.domain is not None


app_settings = AppSettings()
