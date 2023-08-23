from django.contrib import admin

from . import models


@admin.register(models.LocalUser)
class LocalUserAdmin(admin.ModelAdmin):
    list_display = ("person",)
    search_fields = ("person__name", "person__instance__domain")
    readonly_fields = (
        "person",
        "email",
        "theme",
        "default_sort_type",
        "default_listing_type",
        "show_avatars",
        "accepted_application",
        "show_scores",
    )


@admin.register(models.Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = ("name", "actor_id", "local", "instance")
    list_filter = ("banned", "local", "deleted")
    search_fields = ("name", "instance__domain")


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
