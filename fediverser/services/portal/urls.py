from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from django.views.generic.base import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtailautocomplete.urls.admin import urlpatterns as autocomplete_admin_urls

urlpatterns = [
    path("accounts/", include("allauth.urls")),
    path("autocomplete/", include(autocomplete_admin_urls)),
    path("login/", RedirectView.as_view(url="/accounts/login/"), name="login-redirect"),
    path("", include("fediverser.apps.core.urls", namespace="fediverser-core")),
    path("", include(wagtailadmin_urls)),
    path("", include(wagtail_urls)),
]

if settings.DEBUG:
    urlpatterns.extend(static(settings.STATIC_URL, document_root=settings.STATIC_ROOT))
    urlpatterns.extend(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
