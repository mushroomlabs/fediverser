from django import template
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.utils.html import json_script
from django.utils.translation import gettext_lazy as _
from wagtail.admin.ui import sidebar
from wagtail.telepath import JSContext, adapter

from fediverser.apps.core.models.feeds import Entry
from fediverser.apps.core.models.mapping import ChangeRequest
from fediverser.apps.core.models.reddit import RedditCommunity, RedditSubmission
from fediverser.apps.lemmy.services import InstanceProxy

register = template.Library()


@adapter("wagtail.sidebar.WagtailBrandingModule", base=sidebar.BaseSidebarAdapter)
class FediverserBrandingModule:
    def js_args(self):
        return [reverse("fediverser-core:portal-home")]


@register.simple_tag(takes_context=True)
def sidebar_json_script(context, element_id):
    request = context["request"]

    logged_user_menu = [
        sidebar.ActionMenuItem(
            "logout", _("Log out"), reverse("account_logout"), icon_name="logout"
        ),
    ]

    anonymous_user_menu = [
        sidebar.LinkMenuItem(
            "login",
            _("Login"),
            reverse("fediverser-core:reddit-connection-setup"),
            icon_name="login",
        ),
    ]

    account_menu = logged_user_menu if request.user.is_authenticated else anonymous_user_menu
    main_menu = [
        sidebar.LinkMenuItem(
            "instance-list",
            _("Instances"),
            reverse("fediverser-core:instance-list"),
            icon_name="site",
        ),
        sidebar.LinkMenuItem(
            "community-list",
            _("Communities"),
            reverse("fediverser-core:community-list"),
            icon_name="group",
        ),
        sidebar.LinkMenuItem(
            "subreddit-list",
            _("Subreddits"),
            reverse("fediverser-core:subreddit-list"),
            icon_name="group",
        ),
    ]

    if request.user.is_authenticated:
        main_menu.extend(
            [
                sidebar.LinkMenuItem(
                    "activity",
                    _("Activity"),
                    reverse("fediverser-core:activity-list"),
                    icon_name="history",
                )
            ]
        )

    modules = [
        FediverserBrandingModule(),
        sidebar.MainMenuModule(main_menu, account_menu, request.user),
    ]

    return json_script(
        {
            "modules": JSContext().pack(modules),
        },
        element_id=element_id,
    )


@register.filter
def pending_category_proposal(user, subreddit):
    return subreddit.category_change_requests.filter(
        requester=user, status=ChangeRequest.STATUS.requested
    ).last()


@register.filter
def pending_community_recommendations(user, subreddit):
    return subreddit.recommendation_requests.filter(
        requester=user, status=ChangeRequest.STATUS.requested
    )


@register.filter
def is_missing_community_recommendations(subreddit):
    pending_recommendations = subreddit.recommendation_requests.filter(
        status=ChangeRequest.STATUS.requested
    ).exists()

    accepted_recommendations = subreddit.recommendations.exists()

    return not pending_recommendations and not accepted_recommendations


@register.filter
def has_pending_community_recommendations(user, subreddit):
    return (
        user.is_authenticated
        and subreddit.recommendation_requests.filter(
            requester=user, status=ChangeRequest.STATUS.requested
        ).exists()
    )


@register.filter
def has_pending_reddit_status_change_request(user, subreddit):
    return (
        user.is_authenticated
        and subreddit.status_change_requests.filter(
            requester=user, status=ChangeRequest.STATUS.requested
        ).exists()
    )


@register.filter
def pending_instance_category_proposal(user, instance):
    if not user.is_authenticated:
        return instance.category_change_requests.none()

    return instance.category_change_requests.filter(
        requester=user, status=ChangeRequest.STATUS.requested
    ).last()


@register.filter
def has_pending_instance_status_change_request(user, instance):
    return (
        user.is_authenticated
        and instance.status_change_requests.filter(
            requester=user, status=ChangeRequest.STATUS.requested
        ).exists()
    )


@register.filter
def pending_community_category_proposal(user, community):
    if not user.is_authenticated:
        return community.category_change_requests.none()

    return community.category_change_requests.filter(
        requester=user, status=ChangeRequest.STATUS.requested
    ).last()


@register.filter
def has_pending_community_status_change_request(user, community):
    return (
        user.is_authenticated
        and community.status_change_requests.filter(
            requester=user, status=ChangeRequest.STATUS.requested
        ).exists()
    )


@register.filter
def is_subscriber(user, subreddit_name):
    return RedditCommunity.objects.filter(
        name__iexact=subreddit_name, redditaccount__portal_account__user=user
    ).exists()


@register.filter
def is_ambassador(user, community):
    return user.account.representing_communities.filter(community=community).exists()


@register.filter
def has_pending_ambassador_application(user, community):
    return community.ambassador_applications.filter(
        requester=user, status=ChangeRequest.STATUS.requested
    ).exists()


@register.filter
def latest_feed_entries(community):
    now = timezone.now()
    cutoff = now - Entry.MAX_AGE
    entries = Entry.objects.filter(feed__communities__community=community, modified__gte=cutoff)
    return entries.select_related("feed").order_by("-modified")


@register.filter
def submissions_from_related_subreddits(community):
    now = timezone.now()
    cutoff = now - RedditSubmission.MAX_AGE
    return RedditSubmission.objects.filter(
        subreddit__recommendations__community=community, modified__gte=cutoff
    )


@register.filter
def subreddit_counterparts(community):
    return RedditCommunity.objects.filter(recommendations__community=community)


@register.simple_tag
def lemmy_instance():
    return InstanceProxy.get_connected_instance()


@register.simple_tag
def fediverser_hub_site():
    return settings.FEDIVERSER_HUB_SITE


@register.simple_tag
def site_name():
    return settings.SITE_NAME
