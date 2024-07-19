from django.urls import path

from . import views

app_name = "fediverser-core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="portal-home"),
    path("connect/reddit/", views.RedditConnectionView.as_view(), name="reddit-connection-setup"),
    path(
        "onboard/lemmy/start",
        views.SelectLemmyInstanceView.as_view(),
        name="lemmy-onboarding-start",
    ),
    path("activity", views.UserActionListView.as_view(), name="activity-list"),
    path("subreddits", views.SubredditListView.as_view(), name="subreddit-list"),
    path("instances", views.InstanceListView.as_view(), name="instance-list"),
    path("communities", views.CommunityListView.as_view(), name="community-list"),
    path(
        "instances/create",
        views.InstanceCreateView.as_view(),
        name="instance-create",
    ),
    path(
        "instances/<str:domain>",
        views.InstanceDetailView.as_view(),
        name="instance-detail",
    ),
    path(
        "instances/<str:domain>/recommend/category",
        views.InstanceCategoryRecommendationCreateView.as_view(),
        name="instance-categoryrecommendation-create",
    ),
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
    path("subreddits/create", views.SubredditCreateView.as_view(), name="subreddit-create"),
    path("subreddits/<str:name>", views.SubredditDetailView.as_view(), name="subreddit-detail"),
    path("subreddits/<str:name>/lock", views.lock_subreddit, name="subreddit-lock"),
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
    path("api/nodeinfo", views.NodeInfoView.as_view(), name="nodeinfo-detail"),
    path(
        "api/fediverser-instances",
        views.FediversedInstanceListView.as_view(),
        name="fediverserinstance-list",
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
