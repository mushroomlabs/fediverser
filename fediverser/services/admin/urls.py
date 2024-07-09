from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from wagtail.admin import urls as wagtailadmin_urls

urlpatterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + [
    path("cms/", include(wagtailadmin_urls)),
    path("", admin.site.urls),
]
