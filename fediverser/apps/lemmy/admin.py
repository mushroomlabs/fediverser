import datetime

from django.contrib import admin
from django.utils.timezone import make_aware

from . import models


@admin.register(models.LocalUser)
class LocalUserAdmin(admin.ModelAdmin):
    list_display = (
        "person",
        "accepted_application",
        "email_verified",
        "admin",
        "totp_2fa_enabled",
    )

    # list_display = ("person", "email", "theme", "accepted_application", "totp_2fa_enabled")
    list_filter = ("accepted_application", "totp_2fa_enabled", "admin", "email_verified")
    list_select_related = ("person",)
    search_fields = ("person__name", "person__instance__domain")
    readonly_fields = (
        "person",
        "email",
        "default_sort_type",
        "default_listing_type",
        "show_avatars",
        "accepted_application",
        "show_scores",
    )


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    date_hierarchy = "published"
    list_display = (
        "name",
        "instance",
        "actor_id",
        "banned",
        "local",
        "deleted",
        "bot_account",
        "published",
    )
    list_filter = ("banned", "local", "deleted", "bot_account")
    search_fields = ("name", "instance__domain")

    def get_queryset(self, *args, **kw):
        end_date = make_aware(datetime.datetime(year=9999, month=12, day=31))
        qs = super().get_queryset(*args, **kw)
        qs.filter(ban_expires__gt=end_date).update(ban_expires=end_date)
        return qs


@admin.register(models.Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ("domain", "software", "version")
    list_filter = ("software",)
    search_fields = ("domain",)


@admin.register(models.Site)
class SiteAdmin(admin.ModelAdmin):
    pass


@admin.register(models.LocalSite)
class LocalSiteAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("post_id", "content", "language", "deleted", "local")
    list_select_related = ("post",)
    list_filter = ("deleted", "removed", "local", "distinguished", "language")

    def has_change_permission(self, *args, **kw):
        return False


@admin.register(models.Secret)
class SecretAdmin(admin.ModelAdmin):
    def has_change_permission(self, *args, **kw):
        return False


@admin.register(models.LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    date_hierarchy = "published"
    list_display = ("user", "published", "ip", "user_agent")

    def has_change_permission(self, *args, **kw):
        return False
