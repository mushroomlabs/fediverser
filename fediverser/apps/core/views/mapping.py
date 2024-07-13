from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics
from wagtail.snippets.views.snippets import SnippetViewSet

from .. import forms, models, serializers
from ..filters import ChangeRequestFilter, CommunityFilter, InstanceFilter, RedditCommunityFilter
from .common import CreateView, DetailView, ListView, build_breadcrumbs


class SubredditCreateView(CreateView):
    model = models.RedditCommunity
    form_class = forms.SubredditCreateForm
    template_name = "portal/reddit_community/create.tmpl.html"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:subreddit-list", kwargs=self.kwargs)


class CommunityCreateView(CreateView):
    model = models.Community
    form_class = forms.CommunityCreateForm
    template_name = "portal/community/create.tmpl.html"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:community-list", kwargs=self.kwargs)


class InstanceCreateView(CreateView):
    model = models.Instance
    form_class = forms.InstanceCreateForm
    template_name = "portal/instance/create.tmpl.html"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:instance-list", kwargs=self.kwargs)


class CommunityDetailView(DetailView):
    model = models.Community
    view_name = "fediverser-core:community-detail"
    template_name = "portal/community/detail.tmpl.html"

    @property
    def breadcrumb_label(self):
        return self.page_title

    @property
    def page_title(self):
        return self.get_object().fqdn

    def get_object(self, *args, **kw):
        return get_object_or_404(
            self.model, name=self.kwargs["name"], instance__domain=self.kwargs["instance_domain"]
        )

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        context.update(
            {
                "category_picker_form": forms.CommunityCategoryRecommendationForm(),
                "community_feed_form": forms.CommunityFeedForm(),
            }
        )
        return context


class SubredditDetailView(DetailView):
    model = models.RedditCommunity
    template_name = "portal/reddit_community/detail.tmpl.html"

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        subreddit = context["object"]

        context.update(
            {
                "breadcrumbs_items": build_breadcrumbs(),
                "page_title": subreddit.name,
                "header_icon": "group",
                "categories": models.Category.objects.all(),
                "category_picker_form": forms.CategoryPickerForm(),
                "recommended_alternative_form": forms.SubredditAlternativeRecommendationForm(),
                "community_request_form": forms.CommunityRequestForm(),
            }
        )
        return context

    def get_object(self):
        return self.model.objects.get(name__iexact=self.kwargs["name"])


class SubredditAlternativeRecommendationCreateView(CreateView):
    model = models.RecommendCommunity
    form_class = forms.SubredditAlternativeRecommendationForm
    template_name = "portal/community_proposal/create.tmpl.html"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:activity-list")

    def get_subreddit(self):
        return models.RedditCommunity.objects.get(name__iexact=self.kwargs["name"])

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)
        context.update({"subreddit": self.get_subreddit()})
        return context

    def form_valid(self, form):
        form.instance.requester = self.request.user
        form.instance.subreddit = self.get_subreddit()
        return super().form_valid(form)


class SubredditCategoryRecommendationCreateView(CreateView):
    model = models.SetRedditCommunityCategory
    form_class = forms.SubredditCategoryRecommendationForm
    page_title = "Subreddit"
    page_subtitle = "Recommend Category"
    view_name = "fediverser-core:subreddit-categoryrecommendation-create"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:subreddit-detail", kwargs=self.kwargs)

    def form_valid(self, form):
        form.instance.requester = self.request.user
        form.instance.subreddit = models.RedditCommunity.objects.get(
            name__iexact=self.kwargs["name"]
        )
        return super().form_valid(form)


class UserActionListView(LoginRequiredMixin, ListView):
    model = models.ChangeRequest
    template_name = "portal/change_request/list.tmpl.html"
    filterset_class = ChangeRequestFilter
    view_name = "fediverser-core:activity-list"
    breadcrumb_label = "User Activity"
    page_title = "Your Activity"
    header_icon = "history"

    def get_base_queryset(self):
        return (
            models.ChangeRequest.objects.filter(requester=self.request.user)
            .order_by("status_changed")
            .select_subclasses()
        )


class SubredditListView(ListView):
    model = models.RedditCommunity
    filterset_class = RedditCommunityFilter
    template_name = "portal/reddit_community/list.tmpl.html"
    view_name = "fediverser-core:subreddit-list"
    breadcrumb_label = "Subreddits"
    page_title = "Subreddits"
    header_icon = "group"
    header_action_label = "Add new subreddit"
    header_action_url = reverse_lazy("fediverser-core:subreddit-create")

    queryset = (
        models.RedditCommunity.objects.exclude(hidden=True)
        .annotate(total_subscribers=F("metadata__subscribers"))
        .order_by("-metadata__subscribers")
    )

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)
        context.update(
            {
                "category_picker_form": forms.CategoryPickerForm(),
                "community_request_form": forms.CommunityRequestForm(),
            }
        )
        return context


class InstanceListView(ListView):
    model = models.Instance
    template_name = "portal/instance/list.tmpl.html"
    filterset_class = InstanceFilter
    view_name = "fediverser-core:instance-list"
    breadcrumb_label = "Instances"
    page_title = "Instances"
    header_icon = "globe"
    header_action_label = "Add new Instance"
    header_action_url = reverse_lazy("fediverser-core:instance-create")


class InstanceDetailView(DetailView):
    model = models.Instance
    parent_view_class = InstanceListView
    header_icon = "globe"
    view_name = "fediverser-core:instance-detail"
    template_name = "portal/instance/detail.tmpl.html"

    @property
    def breadcrumb_label(self):
        return self.page_title

    @property
    def page_title(self):
        return self.get_object().domain

    def get_object(self, *args, **kw):
        return get_object_or_404(self.model, domain=self.kwargs["domain"])

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        context.update(
            {
                "category_picker_form": forms.InstanceCategoryRecommendationForm(),
            }
        )
        return context


class InstanceCategoryRecommendationCreateView(CreateView):
    model = models.SetInstanceCategory
    form_class = forms.InstanceCategoryRecommendationForm
    page_title = "Instance"
    page_subtitle = "Recommend Category"
    view_name = "fediverser-core:instance-categoryrecommendation-create"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:instance-detail", kwargs=self.kwargs)

    def form_valid(self, form):
        form.instance.requester = self.request.user
        form.instance.instance = models.Instance.objects.get(domain=self.kwargs["domain"])
        return super().form_valid(form)


class CommunityListView(ListView):
    model = models.Community
    template_name = "portal/community/list.tmpl.html"
    filterset_class = CommunityFilter
    view_name = "fediverser-core:community-list"
    breadcrumb_label = "Communities"
    page_title = "Communities"
    header_icon = "group"
    header_action_label = "Add new community"
    header_action_url = reverse_lazy("fediverser-core:community-create")


class CommunityCategoryRecommendationCreateView(CreateView):
    model = models.SetCommunityCategory
    form_class = forms.CommunityCategoryRecommendationForm
    page_title = "Community"
    page_subtitle = "Recommend Category"
    view_name = "fediverser-core:community-categoryrecommendation-create"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:community-detail", kwargs=self.kwargs)

    def form_valid(self, form):
        form.instance.requester = self.request.user
        form.instance.community = models.Community.objects.get(
            name=self.kwargs["name"], instance__domain=self.kwargs["instance_domain"]
        )
        return super().form_valid(form)


class CommunityRequestListView(generics.ListAPIView):
    serializer_class = serializers.CommunityRequestSerializer
    queryset = models.CommunityRequest.objects.all()
    filter_backends = (filters.OrderingFilter,)
    ordering = ("instance__domain", "subreddit__name")


class RedditCommunityListView(generics.ListAPIView):
    serializer_class = serializers.RedditCommunitySerializer
    queryset = models.RedditCommunity.objects.all()
    filterset_class = RedditCommunityFilter
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter)


class CommunityRequestCreateView(CreateView):
    model = models.CommunityRequest
    form_class = forms.CommunityRequestForm
    page_title = "Community Request"
    view_name = "fediverser-core:subreddit-communityrequest-create"

    def get_success_url(self, *args, **kw):
        return reverse("fediverser-core:subreddit-detail", kwargs=self.kwargs)

    def form_valid(self, form):
        form.instance.requested_by = self.request.user
        form.instance.subreddit = models.RedditCommunity.objects.get(
            name__iexact=self.kwargs["name"]
        )
        return super().form_valid(form)


class CommunityFeedCreateView(CreateView):
    model = models.CommunityFeed
    form_class = forms.CommunityFeedForm

    def get_success_url(self, *args, **kw):
        return reverse(
            "fediverser-core:community-detail",
            kwargs=dict(name=self.kwargs["name"], instance_domain=self.kwargs["instance_domain"]),
        )

    def get_community(self):
        return get_object_or_404(
            models.Community,
            name=self.kwargs["name"],
            instance__domain=self.kwargs["instance_domain"],
        )

    def form_valid(self, form):
        form.instance.community = self.get_community()
        community_feed = form.save()
        self.request.user.account.community_feeds.add(community_feed)
        return HttpResponseRedirect(self.get_success_url())


class SubredditViewSet(SnippetViewSet):
    model = models.RedditCommunity
    icon = "list-ul"
    add_to_admin_menu = True
    list_display = ("name", "description", "category", "over18")
    list_filter = ("category", "over18")
    search_fields = ("name",)


class CommunityViewSet(SnippetViewSet):
    model = models.Community
    icon = "group"
    add_to_admin_menu = True
    list_filter = ("category", "status")
    list_display = ("name", "instance", "category")


class InstanceViewSet(SnippetViewSet):
    model = models.Instance
    list_filter = ("category", "status")
    add_to_admin_menu = True


@csrf_exempt
@user_passes_test(lambda u: u.is_staff)
def lock_subreddit(request, *args, **kw):
    name = kw["name"]
    subreddit = get_object_or_404(models.RedditCommunity, name=name)

    if request.method == "POST":
        subreddit.locked = True
        subreddit.save()
    if request.method == "DELETE":
        subreddit.locked = False
        subreddit.save()

    return HttpResponse(status=202)