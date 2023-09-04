from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "fediverser.apps.core"

    def ready(self):
        from . import handlers  # noqa
