from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.blocks import RichTextBlock, TextBlock
from wagtail.fields import StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Orderable, Page
from wagtail.search import index


class Article(Page):
    content = StreamField(
        [
            ("text", RichTextBlock()),
            ("image", ImageChooserBlock()),
            ("warning", TextBlock()),
            ("info", TextBlock()),
        ],
        use_json_field=True,
    )

    search_fields = Page.search_fields + [
        index.FilterField("content"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("content"),
        InlinePanel("related", label="Related"),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    template = "portal/pages/article.tmpl.html"


class PageRelatedLink(Orderable):
    page = ParentalKey(Article, on_delete=models.CASCADE, related_name="related")
    name = models.CharField(max_length=255)
    url = models.URLField()

    panels = [FieldPanel("name"), FieldPanel("url")]


__all__ = ("Article", "PageRelatedLink")
