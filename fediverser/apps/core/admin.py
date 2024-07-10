from django.contrib import admin, messages
from django.db.models import Count

from fediverser.apps.lemmy.services import LemmyClientRateLimited

from . import tasks
from .models.accounts import UserAccount
from .models.activitypub import Community, Instance
from .models.invites import CommunityInviteTemplate
from .models.mapping import Category, ChangeRequest
from .models.mirroring import LemmyMirroredComment, LemmyMirroredPost, RedditMirrorStrategy
from .models.reddit import (
    RedditAccount,
    RedditComment,
    RedditCommunity,
    RedditSubmission,
    RejectedPost,
)


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "reddit_account", "lemmy_local_username")
    list_select_related = ("user", "reddit_account")

    @admin.display(boolean=False, description="username")
    def username(self, obj):
        return obj.user.username

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("description", "requester", "status")
    list_filter = ("status",)

    actions = ("accept_changes", "reject_changes")

    @admin.action(description="Accept requested changes")
    def accept_changes(self, request, queryset):
        for change_request in queryset.select_subclasses():
            change_request.accept()

    @admin.action(description="Reject requested changes")
    def reject_changes(self, request, queryset):
        for change_request in queryset.select_subclasses():
            change_request.reject()

    def get_queryset(self, *args, **kw):
        qs = super().get_queryset(*args, **kw)
        return qs.select_subclasses()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "description")

    @admin.display(boolean=False, description="Category")
    def full_name(self, obj):
        return obj.full_name

    def get_queryset(self, request, *args, **kw):
        qs = super().get_queryset(request, *args, **kw)
        return qs.with_tree_fields()


class CommunityInline(admin.TabularInline):
    model = Community
    fields = ("name",)
    extra = 1


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    search_fields = ("domain",)

    inlines = (CommunityInline,)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "instance")
    list_filter = ("category",)
    list_select_related = ("instance", "category")
    search_fields = ("name", "instance__domain")
    autocomplete_fields = ("instance",)
    readonly_fields = ("instance", "name")


@admin.register(RedditCommunity)
class RedditCommunityAdmin(admin.ModelAdmin):
    change_form_template = "admin/redditcommunity_change_form.html"

    list_display = (
        "name",
        "category",
        "over18",
        "advertiser_category",
        "locked",
        "reported_subscribers",
        "last_synced_at",
    )
    search_fields = ("name",)
    actions = ("get_metadata", "fetch_new_posts")

    @admin.action(description="Fetch new submissions")
    def fetch_new_posts(self, request, queryset):
        for subreddit_name in queryset.values_list("name", flat=True):
            tasks.fetch_new_posts.delay(subreddit_name=subreddit_name)

    @admin.action(description="Fetch Metadata")
    def get_metadata(self, request, queryset):
        for subreddit in queryset:
            subreddit.get_metadata()


@admin.register(RedditAccount)
class RedditAccountAdmin(admin.ModelAdmin):
    list_display = (
        "username",
        "marked_as_spammer",
        "marked_as_bot",
        "rejected_invite",
    )
    list_filter = ("marked_as_spammer", "marked_as_bot")
    search_fields = ("username",)
    actions = ("create_lemmy_mirror", "mark_as_spammer", "unflag_as_spammer", "mark_as_bot")
    autocomplete_fields = ("subreddits",)
    readonly_fields = ("username",)

    @admin.action(description="Flag as spammer")
    def mark_as_spammer(self, request, queryset):
        return queryset.update(marked_as_spammer=True)

    @admin.action(description="Un-flag as spammer")
    def unflag_as_spammer(self, request, queryset):
        return queryset.update(marked_as_spammer=False)

    @admin.action(description="Mark as bot account")
    def mark_as_bot(self, request, queryset):
        return queryset.update(marked_as_bot=True)

    @admin.action(description="Create account on Lemmy Mirror Instance")
    def create_lemmy_mirror(self, request, queryset):
        for account in queryset:
            account.register_mirror()


@admin.register(RedditMirrorStrategy)
class RedditMirrorStrategyAdmin(admin.ModelAdmin):
    list_display = (
        "subreddit",
        "community",
        "automatic_submission_policy",
        "automatic_comment_policy",
        "automatic_submission_limit",
    )
    list_filter = ("automatic_submission_policy", "automatic_comment_policy")
    autocomplete_fields = ("subreddit", "community")


@admin.register(RedditSubmission)
class RedditSubmissionAdmin(ReadOnlyMixin, admin.ModelAdmin):
    change_form_template = "admin/redditsubmission_change_form.html"
    date_hierarchy = "created"
    list_display = (
        "title",
        "subreddit",
        "author",
        "url",
        "status",
        "total_comments",
        "is_spam",
        "is_duplicate",
    )
    list_filter = (
        "subreddit",
        "status",
        "quarantined",
        "removed",
        "marked_as_spam",
        "marked_as_duplicate",
    )
    list_select_related = ("subreddit", "author")
    search_fields = ("id", "title")
    actions = (
        "fetch_from_reddit",
        "post_to_lemmy",
        "post_comments_to_lemmy",
        "send_invite_to_post_author",
        "mark_as_spam",
        "mark_as_duplicate",
        "mark_as_ham",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(total_comments=Count("comments"))

    def total_comments(self, obj):
        return obj.total_comments

    def is_duplicate(self, obj):
        return obj.marked_as_duplicate

    def is_spam(self, obj):
        return obj.marked_as_spam

    is_duplicate.short_description = "Duplicate"
    is_duplicate.boolean = True

    is_spam.short_description = "Spam"
    is_spam.boolean = True

    @admin.action(description="Fetch data from Reddit")
    def fetch_from_reddit(self, request, queryset):
        for reddit_submission in queryset:
            RedditSubmission.make(
                subreddit=reddit_submission.subreddit, post=reddit_submission.praw_object
            )

    @admin.action(description="Post Submission to Lemmy")
    def post_to_lemmy(self, request, queryset):
        for reddit_submission in queryset:
            for community in Community.objects.filter(
                reddittolemmycommunity__subreddit=reddit_submission.subreddit
            ):
                try:
                    LemmyMirroredPost.make_mirror(
                        reddit_submission=reddit_submission, community=community
                    )
                except RejectedPost as exc:
                    reddit_submission.status = RedditSubmission.STATUS.rejected
                    reddit_submission.save()
                    messages.error(request, f"Post {reddit_submission.id} rejected: {exc}")
                except Exception as exc:
                    messages.error(
                        request,
                        f"Failed to post {reddit_submission.id} to {community.name}: {exc}",
                    )

    @admin.action(description="Post comments to Lemmy")
    def post_comments_to_lemmy(self, request, queryset):
        for reddit_submission in queryset:
            for mirrored_post in reddit_submission.lemmy_mirrored_posts.all():
                for comment in reddit_submission.comments.filter(parent=None):
                    try:
                        LemmyMirroredComment.make_mirror(
                            reddit_comment=comment,
                            mirrored_post=mirrored_post,
                            include_children=True,
                        )
                    except LemmyClientRateLimited:
                        messages.warning("Stop due to being rate-limit")
                        return

    @admin.action(description="Send invite to author")
    def send_invite_to_post_author(self, request, queryset):
        posts = queryset.select_related("author", "subreddit")
        for post in posts.exclude(subreddit__invite_templates__isnull=True):
            if post.author.can_send_invite:
                tasks.send_community_invite_to_redditor(
                    redditor_name=post.author.username, subreddit_name=post.subreddit.name
                )

    @admin.action(description="Flag as Spam")
    def mark_as_spam(self, request, queryset):
        return queryset.update(marked_as_spam=True)

    @admin.action(description="Un-flag as Spam")
    def mark_as_ham(self, request, queryset):
        return queryset.update(marked_as_spam=False)

    @admin.action(description="Flag as Duplicate")
    def mark_as_duplicate(self, request, queryset):
        return queryset.update(marked_as_duplicate=True)


@admin.register(RedditComment)
class RedditCommentAdmin(ReadOnlyMixin, admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("submission_id", "author", "body", "is_spam")
    list_filter = ("distinguished", "marked_as_spam", "status")
    actions = ("mark_as_spam", "mark_as_ham")
    search_fields = ("id", "body")

    def is_spam(self, obj):
        return obj.marked_as_spam

    is_spam.short_description = "Spam"
    is_spam.boolean = True

    @admin.action(description="Flag as Spam")
    def mark_as_spam(self, request, queryset):
        return queryset.update(marked_as_spam=True)

    @admin.action(description="Un-flag as Spam")
    def mark_as_ham(self, request, queryset):
        return queryset.update(marked_as_spam=False)


@admin.register(CommunityInviteTemplate)
class CommunityInviteTemplateAdmin(admin.ModelAdmin):
    list_display = ("subreddit", "community")
    list_filter = ("subreddit", "community")
    autocomplete_fields = ("subreddit", "community")


@admin.register(LemmyMirroredComment)
class LemmyMirroredCommentAdmin(admin.ModelAdmin):
    list_display = ("reddit_comment_id", "lemmy_comment_id", "community")
    list_select_related = ("lemmy_mirrored_post", "lemmy_mirrored_post__community")
    list_filter = ("lemmy_mirrored_post__community",)
    search_fields = ("reddit_comment_id", "lemmy_comment_id")

    def community(self, obj):
        return obj.lemmy_mirrored_post.community

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LemmyMirroredPost)
class LemmyMirroredPostAdmin(admin.ModelAdmin):
    list_display = ("reddit_submission", "community")
    list_select_related = ("reddit_submission", "community")
    list_filter = ("community",)

    def has_change_permission(self, request, obj=None):
        return False
