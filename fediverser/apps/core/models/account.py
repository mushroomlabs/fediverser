from django.conf import settings
from django.db import models

from fediverser.apps.lemmy.services import LocalUserProxy

from .reddit import RedditAccount


class UserAccount(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, related_name="account", on_delete=models.CASCADE
    )
    reddit_account = models.OneToOneField(
        RedditAccount,
        related_name="portal_account",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    lemmy_local_username = models.CharField(max_length=255, unique=True, null=True, blank=True)

    @property
    def lemmy_local_user(self):
        return LocalUserProxy.objects.filter(person__name=self.lemmy_local_username).first()

    def check_lemmy_password(self, cleartext):
        return bool(self.lemmy_local_user) and self.lemmy_local_user.check_password(cleartext)


__all__ = ("UserAccount",)
