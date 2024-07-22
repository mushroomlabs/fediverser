import os

import environ

env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = env.str("FEDIVERSER_SECRET_KEY")

DEBUG = env.bool("FEDIVERSER_DEBUG", default=False)
TEST_MODE = env.bool("FEDIVERSER_TEST", default=False)

ALLOWED_HOSTS = ["*"]

CSRF_TRUSTED_ORIGINS = [
    it for it in env.str("FEDIVERSER_CSRF_TRUSTED_ORIGINS", default="").split(",") if it
]

# Application definition
DJANGO_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "django.contrib.humanize",
)

THIRD_PARTY_APPS = (
    "django_celery_beat",
    "django_celery_results",
    "django_countries",
    "django_extensions",
    "django_filters",
    "drf_link_header_pagination",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.reddit",
    "rest_framework",
    "modelcluster",
    "taggit",
    "tree_queries",
    "wagtail.contrib.forms",
    "wagtail.contrib.routable_page",
    "wagtail.contrib.styleguide",
    "wagtail.sites",
    "wagtail.documents",
    "wagtail.snippets",
    "wagtail.users",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "wagtailautocomplete",
)

INTERNAL_APPS = (
    "fediverser.apps.core",
    "fediverser.apps.lemmy",
)

INSTALLED_APPS = INTERNAL_APPS + THIRD_PARTY_APPS + DJANGO_APPS
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# This ensures that requests are seen as secure when the proxy sets the header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = env.str("FEDIVERSER_ROOT_URLCONF", default="fediverser.services.admin.urls")

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": ["templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.static",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "fediverser.services.base.wsgi.application"


# Instance-specific
SITE_NAME = env.str("FEDIVERSER_SITE_NAME", default="Fediverser Portal")
WAGTAIL_SITE_NAME = SITE_NAME
FEDIVERSER_ENABLE_LEMMY_INTEGRATION = env.bool("FEDIVERSER_ENABLE_LEMMY", default=True)

FEDIVERSER = {
    "URL": env.str("FEDIVERSER_PORTAL_URL", default=None),
    "NAME": SITE_NAME,
    "HUB_URL": env.str("FEDIVERSER_HUB_URL", default="https://fediverser.network"),
    "REDDIT_SIGNUP_ENABLED": env.bool("FEDIVERSER_ENABLE_REDDIT_SIGNUP", default=True),
    "GLOBAL_LEMMY_INSTANCE_LOCATOR": env.bool(
        "FEDIVERSER_GLOBAL_LEMMY_INSTANCE_LOCATOR", default=False
    ),
}

FEDIVERSED_LEMMY = (
    {
        "INSTANCE_DOMAIN": env.str("FEDIVERSER_CONNECTED_LEMMY_INSTANCE", default=None),
        "BOT_USERNAME": env.str("FEDIVERSER_BOT_USERNAME", default=None),
        "BOT_PASSWORD": env.str("FEDIVERSER_BOT_PASSWORD", default=None),
    }
    if FEDIVERSER_ENABLE_LEMMY_INTEGRATION
    else {}
)


# Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("FEDIVERSER_CACHE_LOCATION", default="redis://redis:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# Celery
CELERY_BROKER_URL = env.str("FEDIVERSER_BROKER_URL", default="redis://redis:6379/0")

# Database
LEMMY_DB = {
    "ENGINE": env.str("LEMMY_DATABASE_ENGINE", default="django.db.backends.postgresql_psycopg2"),
    "NAME": env.str("LEMMY_DATABASE_NAME", default="lemmy"),
    "USER": env.str("LEMMY_DATABASE_USER", default="lemmy"),
    "PASSWORD": env.str("LEMMY_DATABASE_PASSWORD", default=None),
    "HOST": env.str("LEMMY_DATABASE_HOST", default="lemmy-db"),
    "PORT": env.int("LEMMY_DATABASE_PORT", default=5432),
}

DUMMY_DB = {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": env.str("FEDIVERSER_DATABASE_NAME", default="fediverser"),
        "USER": env.str("FEDIVERSER_DATABASE_USER", default="fediverser"),
        "PASSWORD": env.str("FEDIVERSER_DATABASE_PASSWORD"),
        "HOST": env.str("FEDIVERSER_DATABASE_HOST", default="db"),
        "PORT": env.int("FEDIVERSER_DATABASE_PORT", default=5432),
    },
    "lemmy": LEMMY_DB if FEDIVERSER_ENABLE_LEMMY_INTEGRATION else DUMMY_DB,
}
DATABASE_ROUTERS = ("fediverser.services.base.database_router.InternalRouter",)

# Authentication and Account Management
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Email
DEFAULT_FROM_EMAIL = env.str("FEDIVERSER_EMAIL_MAILER_ADDRESS", default="mailer@fediverser")
EMAIL_BACKEND = env.str(
    "FEDIVERSER_EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env.str("FEDIVERSER_EMAIL_HOST", default=None)
EMAIL_PORT = env.str("FEDIVERSER_EMAIL_PORT", default=None)
EMAIL_HOST_USER = env.str("FEDIVERSER_EMAIL_SMTP_USERNAME", default=None)
EMAIL_HOST_PASSWORD = env.str("FEDIVERSER_EMAIL_SMTP_PASSWORD", default=None)
EMAIL_TIMEOUT = env.str("FEDIVERSER_EMAIL_TIMEOUT", 5)


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Reddit
REDDIT_CLIENT_ID = env.str("FEDIVERSER_REDDIT_CLIENT_ID", default=None)
REDDIT_CLIENT_SECRET = env.str("FEDIVERSER_REDDIT_CLIENT_SECRET", default=None)
REDDIT_USER_AGENT = env.str("FEDIVERSER_REDDIT_USER_AGENT", default="fediverser/0.1.0")
REDDIT_BOT_ACCOUNT_USERNAME = env.str("REDDIT_BOT_ACCOUNT_USERNAME", default=None)
REDDIT_BOT_ACCOUNT_PASSWORD = env.str("REDDIT_BOT_ACCOUNT_PASSWORD", default=None)

# Authentication with third-party providers

LOGIN_REDIRECT_URL = "fediverser-core:portal-home"
LOGIN_URL = "account_login"

ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_PRESERVE_USERNAME_CASING = False

ACCOUNT_FORMS = {"signup": "fediverser.apps.core.forms.SignupForm"}

SOCIALACCOUNT_PROVIDERS = {
    "reddit": {
        "AUTH_PARAMS": {"duration": "permanent", "access_type": "offline"},
        "SCOPE": [
            "identity",
            "mysubreddits",
            #            "privatemessages",
            #            "read",
            #            "submit",
        ],
        "USER_AGENT": env.str("FEDIVERSER_USER_AGENT", default=REDDIT_USER_AGENT),
    },
}

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)


STATIC_URL = env.str("FEDIVERSER_STATIC_URL", default="/static/")
STATIC_ROOT = env.str(
    "FEDIVERSER_STATIC_ROOT", default=os.path.abspath(os.path.join(BASE_DIR, "static"))
)
MEDIA_ROOT = os.getenv("FEDIVERSER_MEDIA_ROOT", os.path.abspath(os.path.join(BASE_DIR, "media")))
MEDIA_URL = os.getenv("FEDIVERSER_MEDIA_URL", "/media/")


# Rest Framework
REST_RENDERERS = ("BrowsableAPIRenderer", "JSONRenderer") if DEBUG else ("JSONRenderer",)
REST_FRAMEWORK = {
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_RENDERER_CLASSES": [
        f"rest_framework.renderers.{renderer}" for renderer in REST_RENDERERS
    ],
    "DEFAULT_PAGINATION_CLASS": "drf_link_header_pagination.LinkHeaderPagination",
    "PAGE_SIZE": 100,
}


# Logging Configuration
LOG_LEVEL = os.getenv("FEDIVERSER_LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
LOGGING_HANDLERS = {
    "null": {"level": "DEBUG", "class": "logging.NullHandler"},
    "console": {"level": LOG_LEVEL, "class": "logging.StreamHandler", "formatter": "verbose"},
}

LOGGING_HANDLER_METHODS = ["console"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": "FEDIVERSER_LOG_DISABLE_EXISTING_LOGGERS" in os.environ,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)s:%(pathname)s %(process)d %(lineno)d %(message)s"
        },
        "simple": {"format": "%(levelname)s:%(module)s %(lineno)d %(message)s"},
    },
    "handlers": LOGGING_HANDLERS,
    "loggers": {
        "django": {"handlers": ["null"], "propagate": True, "level": "INFO"},
    },
}

# External libraries that we want to have logs
for module in ("django.request", "praw", "prawcore"):
    LOGGING["loggers"][module] = {
        "handlers": LOGGING_HANDLER_METHODS,
        "level": LOG_LEVEL,
        "propagate": False,
    }

# Set up loggers for our own apps
for app in INTERNAL_APPS:
    LOGGING["loggers"][app] = {
        "handlers": LOGGING_HANDLER_METHODS,
        "level": LOG_LEVEL,
        "propagate": False,
    }
