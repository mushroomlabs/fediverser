from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics

from .. import models, serializers
from ..filters import RedditCommunityFilter
from .common import DetailView, ListView


class RedditorListView(ListView):
    model = models.RedditAccount
    template_name = "portal/redditor/list.tmpl.html"
    page_title = "Redditors"


class RedditorDetailView(DetailView):
    model = models.RedditAccount
    template_name = "portal/redditor/detail.tmpl.html"
    header_icon = "user"

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        redditor = context["object"]

        context.update(
            {
                "page_title": redditor.username,
            }
        )
        return context

    def get_object(self):
        return get_object_or_404(self.model, username=self.kwargs["username"])


class RedditCommunityListView(generics.ListAPIView):
    serializer_class = serializers.RedditCommunitySerializer
    queryset = models.RedditCommunity.objects.all()
    filterset_class = RedditCommunityFilter
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    ordering = ("name",)
    search_fields = ("name",)


class RedditCommunityDetailView(generics.RetrieveAPIView):
    serializer_class = serializers.RedditCommunitySerializer
    queryset = models.RedditCommunity.objects.all()
    lookup_field = "name"

    def get_object(self, *args, **kw):
        return get_object_or_404(models.RedditCommunity, name=self.kwargs["name"])


class RedditSubmissionView(DetailView):
    model = models.RedditSubmission
    template_name = "portal/reddit_submission/detail.tmpl.html"
    header_icon = "post"

    @property
    def page_title(self):
        submission = self.get_object()
        return submission.title

    def get_object(self):
        return get_object_or_404(self.model, id=self.kwargs["submission_id"])


__all__ = (
    "RedditorListView",
    "RedditorDetailView",
    "RedditSubmissionView",
    "RedditCommunityListView",
    "RedditCommunityDetailView",
)
