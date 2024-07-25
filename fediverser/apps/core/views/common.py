from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.urls import reverse
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView as BaseDetailView
from django.views.generic.edit import CreateView as BaseCreateView, FormView as BaseFormView
from django.views.generic.list import ListView as BaseListView


def build_breadcrumbs():
    return [dict(url=reverse("fediverser-core:portal-home"), label="Home")]


class FormView(LoginRequiredMixin, BaseFormView):
    template_name = "portal/generic/form.tmpl.html"
    view_name = None
    breadcrumb_label = None
    page_title = None
    page_subtitle = None
    header_icon = None
    submit_button_label = "Submit"

    @property
    def action_url(self):
        return self.view_name and reverse(self.view_name)

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        breadcrumb_items = build_breadcrumbs()

        if self.action_url and self.breadcrumb_label:
            breadcrumb_items.append(dict(url=self.action_url, label=self.breadcrumb_label))

        context.update(
            {
                "breadcrumbs_items": breadcrumb_items,
                "page_title": self.page_title,
                "page_subtitle": self.page_subtitle,
                "header_icon": self.header_icon,
                "action_url": self.action_url,
                "submit_button_label": self.submit_button_label,
            }
        )
        return context


class CreateView(LoginRequiredMixin, BaseCreateView):
    template_name = "portal/generic/create.tmpl.html"
    view_name = None
    breadcrumb_label = None
    page_title = None
    page_subtitle = None
    header_icon = None

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        breadcrumb_items = build_breadcrumbs()

        if self.view_name and self.breadcrumb_label:
            breadcrumb_items.append(dict(url=reverse(self.view_name), label=self.breadcrumb_label))

        context.update(
            {
                "breadcrumbs_items": breadcrumb_items,
                "page_title": self.page_title,
                "page_subtitle": self.page_subtitle,
                "header_icon": self.header_icon,
            }
        )
        return context


class ListView(BaseListView):
    PAGE_SIZE = 25
    view_name = None
    breadcrumb_label = None
    page_title = None
    header_icon = None
    filterset_class = None
    header_action_label = None
    header_action_url = None

    def get_filter_set_kwargs(self):
        return {
            "request": self.request,
            "data": self.request.GET,
            "queryset": self.get_base_queryset(),
        }

    @property
    def page(self):
        page_number = self.request.GET.get("p", 1)
        return self.paginator.page(page_number)

    def get_base_queryset(self):
        return super().get_queryset()

    @property
    def filter(self):
        if not hasattr(self, "_filter"):
            self._filter = self.filterset_class and self.filterset_class(
                **self.get_filter_set_kwargs()
            )
        return self._filter

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            self._paginator = Paginator(self.get_queryset(), getattr(self, "PAGE_SIZE", 100))
        return self._paginator

    def get_queryset(self):
        return self.get_base_queryset() if not self.filter else self.filter.qs

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        breadcrumb_items = build_breadcrumbs()

        if self.view_name and self.breadcrumb_label:
            breadcrumb_items.append(dict(url=reverse(self.view_name), label=self.breadcrumb_label))

        context.update(
            {
                "breadcrumbs_items": breadcrumb_items,
                "page_title": self.page_title,
                "header_icon": self.header_icon,
                "header_action_label": self.header_action_label,
                "header_action_url": self.header_action_url,
                "is_paginated": True,
                "paginator": self.paginator,
                "page_obj": self.page,
                "filters": self.filter,
                "object_list": self.page.object_list,
            }
        )
        return context


class DetailView(BaseDetailView):
    view_name = None
    page_title = None
    header_icon = None
    parent_view_class = None
    template_name = "portal/generic/detail.tmpl.html"

    @property
    def breadcrumb_label(self):
        return self.model._meta.verbose_name.title()

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        breadcrumb_items = build_breadcrumbs()

        if self.parent_view_class is not None:
            breadcrumb_items.append(
                dict(
                    url=reverse(self.parent_view_class.view_name),
                    label=self.parent_view_class.breadcrumb_label,
                )
            )

        breadcrumb_items.append(dict(url=self.request.path, label=self.breadcrumb_label))

        context.update(
            {
                "breadcrumbs_items": breadcrumb_items,
                "page_title": self.page_title,
                "header_icon": self.header_icon,
            }
        )
        return context


class SimplePageView(LoginRequiredMixin, TemplateView):
    view_name = None
    page_title = None
    header_icon = None

    @property
    def breadcrumb_label(self):
        return self.page_title

    def get_context_data(self, *args, **kw):
        context = super().get_context_data(*args, **kw)

        breadcrumb_items = build_breadcrumbs()
        breadcrumb_items.append(dict(url=self.request.path, label=self.breadcrumb_label))

        context.update(
            {
                "breadcrumbs_items": breadcrumb_items,
                "page_title": self.page_title,
                "header_icon": self.header_icon,
            }
        )
        return context
