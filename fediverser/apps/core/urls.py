from django.urls import path

from . import views

app_name = "fediverser-core"

urlpatterns = [
    path("", views.HomeView.as_view(), name="portal-home"),
    path("connect/reddit/", views.RedditConnectionView.as_view(), name="reddit-connection-setup"),
]
