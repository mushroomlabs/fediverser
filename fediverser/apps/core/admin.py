from django.contrib import admin, messages
from django.db.models import Count

from fediverser.apps.lemmy.services import LemmyClientRateLimited

from . import tasks
from .models.accounts import RedditAccountAuthorizedScope, UserAccount
from .models.activitypub import Community, Instance
from .models.feeds import CommunityFeed, Entry, Feed
from .models.invites import InviteTemplate, RedditorInvite
from .models.mapping import (
    Category,
    ChangeRequest,
    CommunityAnnotation,
    InstanceAnnotation,
    InstanceTopic,
    RedditToCommunityRecommendation,
    SubredditAnnotation,
    Topic,
)
from .models.mirroring import LemmyMirroredComment, LemmyMirroredPost, RedditMirrorStrategy
from .models.network import (
    ChangeFeedEntry,
    FediversedInstance,
    RedditToCommunityRecommendationEntry,
)
from .models.reddit import (
    RedditAccount,
    RedditApplicationKey,
    RedditComment,
    RedditCommunity,
    RedditSubmission,
    RejectedPost,
)
from .settings import app_settings


class ReadOnlyMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(UserAccount)
class UserAccountAdmin(admin.ModelAdmin):
    list_display = ("username", "lemmy_local_username")
    list_select_related = ("user",)

    @admin.display(boolean=False, description="username")
    def username(self, obj):
        return obj.user.username

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RedditAccountAuthorizedScope)
class RedditAccountAuthorizedScopesAdmin(admin.ModelAdmin):
    list_display = ("username", "scope")
    list_filter = ("scope",)

    @admin.display(boolean=False, description="User name")
    def username(self, obj):
        return obj.social_account.uid


@admin.register(Feed)
class FeedAdmin(admin.ModelAdmin):
    date_hierarchy = "last_fetched"
    list_display = ("url", "title", "last_fetched")

    actions = ("fetch_feeds",)

    @admin.action(description="Fetch entries for selected feeds")
    def fetch_feeds(self, request, queryset):
        for feed in queryset:
            try:
                feed.fetch(force=True)
                messages.success(request, f"Feed {feed.url} has been updated")
            except Exception as exc:
                messages.error(request, f"Failed to fetch {feed.url}: {exc}")


@admin.register(Entry)
class FeedEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("link", "title", "feed", "created", "modified")
    list_filter = ("feed",)


@admin.register(CommunityFeed)
class CommunityFeedAdmin(admin.ModelAdmin):
    list_display = ("feed", "community")


@admin.register(ChangeFeedEntry)
class ChangeFeedEntryAdmin(admin.ModelAdmin):
    date_hierarchy = "created"
    list_display = ("published_by", "description", "merged_on")
    actions = ("merge_entries",)

    @admin.action(description="Merge selected entries into our database")
    def merge_entries(self, request, queryset):
        good = 0
        for entry in queryset:
            try:
                entry.merge()
                good += 1
            except Exception as exc:
                messages.error(request, f"Failed to merge {entry.description}: {exc}")
        if good:
            messages.success(request, f"Merged {good} entries")

    def _get_subclassed_qs(self, qs):
        return qs.select_subclasses()

    def get_queryset(self, *args, **kw):
        qs = self._get_subclassed_qs(super().get_queryset(*args, **kw))
        return qs.prefetch_related("merge_info")


@admin.register(RedditToCommunityRecommendationEntry)
class RedditToCommunityRecommendationEntryAdmin(ChangeFeedEntryAdmin):
    list_display = ("published_by", "description", "merged_on")

    def _get_subclassed_qs(self, qs):
        return qs


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


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "description")


@admin.register(InstanceTopic)
class InstanceTopicAdmin(admin.ModelAdmin):
    list_display = ("instance", "topic")
    list_filter = ("topic",)
    autocomplete_fields = ("instance",)


class CommunityInline(admin.TabularInline):
    model = Community
    fields = ("name",)
    extra = 1


@admin.register(Instance)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ("domain", "status", "locked", "category")
    search_fields = ("domain",)

    inlines = (CommunityInline,)

    @admin.display(boolean=False, description="status")
    def status(self, obj):
        try:
            return obj.annotation.status
        except AttributeError:
            return None

    @admin.display(boolean=False, description="category")
    def category(self, obj):
        try:
            return obj.annotation.category
        except AttributeError:
            return None

    @admin.display(boolean=True, description="locked")
    def locked(self, obj):
        try:
            return obj.annotation.locked
        except AttributeError:
            return False

    def get_queryset(self, *args, **kw):
        qs = super().get_queryset(*args, **kw)
        return qs.prefetch_related("annotation")


@admin.register(FediversedInstance)
class FediversedInstanceAdmin(admin.ModelAdmin):
    list_display = (
        "portal_url",
        "instance",
        "allows_reddit_signup",
        "allows_reddit_mirrored_content",
        "accepts_community_requests",
    )
    list_filter = (
        "allows_reddit_signup",
        "allows_reddit_mirrored_content",
        "accepts_community_requests",
    )
    list_select_related = ("instance",)
    search_fields = (
        "portal_url",
        "instance__domain",
    )
    readonly_fields = (
        "instance",
        "allows_reddit_signup",
        "allows_reddit_mirrored_content",
        "accepts_community_requests",
        "creates_reddit_mirror_bots",
    )
    actions = ("submit_registration", "fetch_instance_info", "endorse_instances")

    @admin.action(description="Mark selected instances as trusted")
    def endorse_instances(self, request, queryset):
        our_instance = FediversedInstance.current()
        for instance in queryset:
            try:
                assert (
                    instance != our_instance
                ), f"Skipping {instance.portal_url}: can not endorse ourselves"
                our_instance.endorse(instance)
                messages.success(request, f"Endorsed {instance.portal_url}")
            except AssertionError as exc:
                messages.warning(request, str(exc))
            except Exception as exc:
                messages.error(request, f"Could not endorse {instance.portal_url}: {exc}")

    @admin.action(description="Fetch information from selected instances")
    def fetch_instance_info(self, request, queryset):
        for instance in queryset.exclude(portal_url=None):
            try:
                FediversedInstance.fetch(instance.portal_url)
                messages.success(request, f"Fetched {instance.portal_url}")
            except Exception as exc:
                messages.error(request, f"Failed to fetch data at {instance.portal_url}: {exc}")

    @admin.action(description="Register own instance on selected instances")
    def submit_registration(self, request, queryset):
        own_instance = FediversedInstance.current()
        for instance in queryset:
            try:
                own_instance.submit_registration(instance)
                messages.success(request, f"Registered at {instance.portal_url}")
            except Exception as exc:
                messages.error(request, f"Failed to register at {instance.portal_url}: {exc}")

    def has_change_permission(self, request, obj=None):
        return obj is None or obj.portal_url == app_settings.Portal.url


class AnnotationAdmin(admin.ModelAdmin):
    list_filter = ("status", "hidden", "locked")


@admin.register(CommunityAnnotation)
class CommunityAnnotationAdmin(AnnotationAdmin):
    list_display = ("community", "status", "category", "hidden", "locked")
    list_select_related = ("community", "category")
    search_fields = ("community__name", "community__instance__domain")


@admin.register(InstanceAnnotation)
class InstanceAnnotationAdmin(AnnotationAdmin):
    list_display = (
        "instance",
        "status",
    )
    list_select_related = ("instance",)
    search_fields = ("instance__domain",)


@admin.register(SubredditAnnotation)
class SubredditAnnotationAdmin(AnnotationAdmin):
    list_display = ("subreddit", "status", "category")
    list_select_related = ("subreddit", "category")
    search_fields = ("subreddit__name",)


@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ("name", "instance")
    list_select_related = ("instance",)
    search_fields = ("name", "instance__domain")
    autocomplete_fields = ("instance",)

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RedditCommunity)
class RedditCommunityAdmin(admin.ModelAdmin):
    change_form_template = "admin/redditcommunity_change_form.html"

    list_display = (
        "name",
        "advertiser_category",
        "reported_subscribers",
        "last_synced_at",
        "over18",
        "locked",
    )
    search_fields = ("name",)
    actions = ("get_metadata", "fetch_new_posts", "lock_subreddits")

    @admin.display(boolean=True, description="locked")
    def locked(self, obj):
        try:
            return obj.annotation.locked
        except AttributeError:
            return False

    @admin.action(description="Fetch new submissions")
    def fetch_new_posts(self, request, queryset):
        for subreddit_name in queryset.values_list("name", flat=True):
            tasks.fetch_new_posts.delay(subreddit_name=subreddit_name)

    @admin.action(description="Fetch Metadata")
    def get_metadata(self, request, queryset):
        for subreddit in queryset:
            subreddit.get_metadata()

    @admin.action(description="Lock selected subreddits")
    def lock_subreddits(self, request, queryset):
        SubredditAnnotation.objects.filter(subreddit__in=queryset).update(locked=True)


@admin.register(RedditToCommunityRecommendation)
class RedditToCommunityRecommendationAdmin(admin.ModelAdmin):
    list_display = ("subreddit", "community")
    list_select_related = ("subreddit", "community")
    search_fields = ("subreddit__name", "community__name", "community__instance__domain")


@admin.register(RedditApplicationKey)
class RedditApplicationKeyAdmin(admin.ModelAdmin):
    list_display = ("owner", "client_id")
    autocomplete_fields = ("owner",)


@admin.register(RedditAccount)
class RedditAccountAdmin(admin.ModelAdmin):
    change_form_template = "admin/redditaccount_change_form.html"
    date_hierarchy = "created"
    list_display = (
        "username",
        "suspended",
        "blocked",
        "marked_as_spammer",
        "marked_as_bot",
        "created",
    )
    list_filter = ("suspended", "blocked", "marked_as_spammer", "marked_as_bot")
    search_fields = ("username",)
    actions = ("mark_as_spammer", "unflag_as_spammer", "mark_as_bot")
    autocomplete_fields = ("subreddits",)
    readonly_fields = ("subreddits", "username")

    @admin.action(description="Flag as spammer")
    def mark_as_spammer(self, request, queryset):
        return queryset.update(marked_as_spammer=True)

    @admin.action(description="Un-flag as spammer")
    def unflag_as_spammer(self, request, queryset):
        return queryset.update(marked_as_spammer=False)

    @admin.action(description="Mark as bot account")
    def mark_as_bot(self, request, queryset):
        return queryset.update(marked_as_bot=True)


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
                subreddit=reddit_submission.subreddit,
                post=reddit_submission.praw_object,
                make_comments=True,
            )

    @admin.action(description="Post Submission to Lemmy")
    def post_to_lemmy(self, request, queryset):
        for reddit_submission in queryset:
            for community in Community.objects.filter(
                mirroring_strategies__subreddit=reddit_submission.subreddit
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


@admin.register(InviteTemplate)
class InviteTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "message")


@admin.register(RedditorInvite)
class RedditorInviteAdmin(admin.ModelAdmin):
    list_display = ("redditor", "sent", "accepted")
    list_filter = ("accepted",)


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
