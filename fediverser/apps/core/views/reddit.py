from django.shortcuts import get_object_or_404

from .. import models
from .common import DetailView, ListView, build_breadcrumbs


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
                "breadcrumbs_items": build_breadcrumbs(),
                "page_title": redditor.username,
            }
        )
        return context

    def get_object(self):
        return get_object_or_404(self.model, username=self.kwargs["username"])


__all__ = ("RedditorListView", "RedditorDetailView")
