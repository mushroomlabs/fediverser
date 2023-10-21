from django.urls import path
from django.views.generic.base import TemplateView

from . import views

app_name = "web"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("about", TemplateView.as_view(template_name="web/about.tmpl.html"), name="about"),
    path("connect/reddit", views.RedditConnectionView.as_view(), name="reddit-connection-setup"),
]
