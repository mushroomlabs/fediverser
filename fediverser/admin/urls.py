from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

urlpatterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + [
    path("", admin.site.urls)
]
