from django.urls import path

from . import views

app_name = "fediverser-core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="portal-home"),
    path(
        "reddit/invites/<str:key>/accept",
        views.RedditorAcceptInviteView.as_view(),
        name="redditor-accept-invite",
    ),
    path(
        "reddit/invites/<str:key>/decline",
        views.RedditorDeclineInviteView.as_view(),
        name="redditor-decline-invite",
    ),
    path("reddit/connect", views.RedditConnectionView.as_view(), name="reddit-connection-setup"),
    path("reddit/login", views.RedditLoginView.as_view(), name="reddit-login"),
    path("lemmy/connect", views.LemmySignupView.as_view(), name="lemmy-connect-setup"),
    path("lemmy/set-password", views.LemmySetPasswordView.as_view(), name="lemmy-set-password"),
    path("activity", views.UserActionListView.as_view(), name="activity-list"),
    path("instances", views.InstanceListView.as_view(), name="instance-list"),
    path("instances/create", views.InstanceCreateView.as_view(), name="instance-create"),
    path("instances/find", views.InstanceFinderView.as_view(), name="instance-find"),
    path("instances/<str:domain>", views.InstanceDetailView.as_view(), name="instance-detail"),
    path(
        "instances/<str:domain>/recommend/category",
        views.InstanceCategoryRecommendationCreateView.as_view(),
        name="instance-categoryrecommendation-create",
    ),
    path(
        "instances/<str:domain>/recommend/country",
        views.InstanceCountryRecommendationCreateView.as_view(),
        name="instance-countryrecommendation-create",
    ),
    path(
        "instances/<str:domain>/annotate/closed",
        views.InstanceClosedAnnotationCreateView.as_view(),
        name="instance-closedannotation-create",
    ),
    path(
        "instances/<str:domain>/annotate/abandoned",
        views.InstanceAbandonedAnnotationCreateView.as_view(),
        name="instance-abandonedannotation-create",
    ),
    path("communities", views.CommunityListView.as_view(), name="community-list"),
    path(
        "communities/create",
        views.CommunityCreateView.as_view(),
        name="community-create",
    ),
    path(
        "communities/<str:name>@<str:instance_domain>",
        views.CommunityDetailView.as_view(),
        name="community-detail",
    ),
    path(
        "communities/<str:name>@<str:instance_domain>/repost/reddit",
        views.CommunityRepostRedditSubmissionView.as_view(),
        name="community-repost-reddit",
    ),
    path(
        "communities/<str:name>@<str:instance_domain>/recommend/category",
        views.CommunityCategoryRecommendationCreateView.as_view(),
        name="community-categoryrecommendation-create",
    ),
    path(
        "communities/<str:name>@<str:instance_domain>/ambassadors/apply",
        views.CommunityAmbassadorApplicationCreateView.as_view(),
        name="community-ambassador-application-create",
    ),
    path(
        "communities/<str:name>@<str:instance_domain>/feeds/create",
        views.CommunityFeedCreateView.as_view(),
        name="community-contentfeed-create",
    ),
    path(
        "reddit/submissions/<str:submission_id>",
        views.RedditSubmissionView.as_view(),
        name="redditsubmission-detail",
    ),
    path("subreddits", views.SubredditListView.as_view(), name="subreddit-list"),
    path("subreddits/create", views.SubredditCreateView.as_view(), name="subreddit-create"),
    path("subreddits/<str:name>", views.SubredditDetailView.as_view(), name="subreddit-detail"),
    path(
        "subreddits/<str:name>/subscribe", views.subscribe_to_subreddit, name="subreddit-subscribe"
    ),
    path(
        "subreddits/<str:name>/unsubscribe",
        views.unsubscribe_from_subreddit,
        name="subreddit-unsubscribe",
    ),
    path(
        "subreddits/<str:name>/recommend/category",
        views.SubredditCategoryRecommendationCreateView.as_view(),
        name="subreddit-categoryrecommendation-create",
    ),
    path(
        "subreddits/<str:name>/recommend/alternative",
        views.SubredditAlternativeRecommendationCreateView.as_view(),
        name="subreddit-alternativerecommendation-create",
    ),
    path(
        "subreddits/<str:name>/request/community",
        views.CommunityRequestCreateView.as_view(),
        name="subreddit-communityrequest-create",
    ),
    path("redditors", views.RedditorListView.as_view(), name="redditor-list"),
    path("redditors/<str:username>", views.RedditorDetailView.as_view(), name="redditor-detail"),
    path(
        "redditors/<str:username>/invite",
        views.RedditorInviteView.as_view(),
        name="redditor-send-invite",
    ),
    path(
        "api/community-requests",
        views.CommunityRequestListView.as_view(),
        name="api-community-request-list",
    ),
    path(
        "api/subreddits",
        views.RedditCommunityListView.as_view(),
        name="api-subreddit-list",
    ),
    path(
        "api/subreddits/<str:name>",
        views.RedditCommunityDetailView.as_view(),
        name="api-subreddit-detail",
    ),
    path(
        "api/subreddits/<str:name>/alternatives",
        views.SubredditAlternativeRecommendationListView.as_view(),
        name="api-subredditalternative-list",
    ),
    path("api/nodeinfo", views.NodeInfoView.as_view(), name="nodeinfo-detail"),
    path(
        "api/fediverser-instances",
        views.FediversedInstanceListView.as_view(),
        name="fediverserinstance-list",
    ),
    path(
        "api/instance/recommendations",
        views.InstanceRecommendationsListView.as_view(),
        name="api-instancerecommendation-list",
    ),
    path(
        "api/changes",
        views.ChangeFeedEntryListView.as_view(),
        name="changefeedentry-list",
    ),
    path(
        "api/changes/<int:pk>",
        views.ChangeFeedEntryDetailView.as_view(),
        name="changefeedentry-detail",
    ),
    path("feed/changes", views.ChangeFeed(), name="changefeed-feed"),
]
