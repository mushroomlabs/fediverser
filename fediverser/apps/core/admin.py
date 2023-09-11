from django.contrib import admin

from . import models, tasks


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
    search_fields = ("name",)

    actions = ("fetch_new_posts",)

    @admin.action(description="Fetch new submissions")
    def fetch_new_posts(self, request, queryset):
        for subreddit_name in queryset.values_list("name", flat=True):
            tasks.fetch_new_posts.delay(subreddit_name=subreddit_name)


@admin.register(models.RedditAccount)
class RedditAccountAdmin(admin.ModelAdmin):
    list_display = ("username",)
    search_fields = ("username",)
    actions = ("create_lemmy_mirror",)

    @admin.action(description="Create account on Lemmy Mirror Instance")
    def create_lemmy_mirror(self, request, queryset):
        for account in queryset:
            account.register_mirror()


@admin.register(models.RedditToLemmyCommunity)
class RedditToLemmyCommunityAdmin(admin.ModelAdmin):
    list_display = ("subreddit", "lemmy_community")
    autocomplete_fields = ("subreddit", "lemmy_community")


@admin.register(models.RedditSubmission)
class RedditSubmissionAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = (
        "title",
        "subreddit",
        "author",
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
    list_select_related = ("subreddit", "author")
    search_fields = ("title",)
    actions = ("fetch_from_reddit", "post_to_lemmy", "send_invite_to_post_author")

    @admin.action(description="Fetch data from Reddit")
    def fetch_from_reddit(self, request, queryset):
        for reddit_submission in queryset:
            models.RedditSubmission.make(
                subreddit=reddit_submission.subreddit, post=reddit_submission.praw_object
            )

    @admin.action(description="Post to on Mirror Communities")
    def post_to_lemmy(self, request, queryset):
        for post in queryset:
            post.make_mirror()

    @admin.action(description="Send invite to author")
    def send_invite_to_post_author(self, request, queryset):
        posts = queryset.select_related("author", "subreddit")
        for post in posts.exclude(subreddit__invite_templates__isnull=True):
            if post.author.can_send_invite:
                tasks.send_lemmy_community_invite_to_redditor(
                    redditor_name=post.author.username, subreddit_name=post.subreddit.name
                )


@admin.register(models.RedditComment)
class RedditCommentAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("submission", "author")
    list_filter = ("distinguished",)


@admin.register(models.LemmyCommunityInviteTemplate)
class LemmyCommunityInviteTemplateAdmin(admin.ModelAdmin):
    list_display = ("subreddit", "lemmy_community")
    list_filter = ("subreddit", "lemmy_community")
    autocomplete_fields = ("subreddit", "lemmy_community")
