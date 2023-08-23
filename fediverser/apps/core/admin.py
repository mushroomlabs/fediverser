from django.contrib import admin

from . import models


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.LemmyInstance)
class LemmyInstanceAdmin(admin.ModelAdmin):
    search_fields = ("domain",)


@admin.register(models.LemmyCommunity)
class LemmyCommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "instance")
    list_select_related = ("instance",)
    search_fields = ("name", "instance__domain")
    autocomplete_fields = ("instance",)


@admin.register(models.RedditCommunity)
class RedditCommunityAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(models.RedditAccount)
class RedditAccountAdmin(admin.ModelAdmin):
    list_display = ("username",)
    search_fields = ("username",)


@admin.register(models.RedditToLemmyCommunity)
class RedditToLemmyCommunityAdmin(admin.ModelAdmin):
    list_display = ("subreddit", "lemmy_community")


@admin.register(models.RedditSubmission)
class RedditSubmissionAdmin(ReadOnlyMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "subreddit",
        "url",
        "media_only",
        "locked",
        "quarantined",
        "removed",
        "over_18",
        "archived",
    )
    list_filter = (
        "subreddit",
        "media_only",
        "locked",
        "quarantined",
        "removed",
        "over_18",
        "archived",
    )
    search_fields = ("title",)


@admin.register(models.RedditComment)
class RedditCommentAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("submission", "author")
    list_filter = ("distinguished",)
