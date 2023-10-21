import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fediverser.services.base.settings")
os.environ.setdefault("FEDIVERSER_ROOT_URLCONF", "fediverser.services.admin.urls")

application = get_asgi_application()
