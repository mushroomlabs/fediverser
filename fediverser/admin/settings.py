import os

import environ

env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(PROJECT_DIR)

SECRET_KEY = env.str("FEDIVERSER_SECRET_KEY")

DEBUG = env.bool("FEDIVERSER_DEBUG", default=False)

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
)

THIRD_PARTY_APPS = (
    "django_celery_beat",
    "django_celery_results",
    "django_extensions",
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
]

CORS_ALLOW_ALL_ORIGINS = True
ROOT_URLCONF = env.str("FEDIVERSER_ROOT_URLCONF", default="fediverser.admin.urls")

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

WSGI_APPLICATION = "fediverser.admin.wsgi.application"

# Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.str("CACHE_URL", default="redis://redis:6379/1"),
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}

# Celery

CELERY_BROKER_URL = env.str("FEDIVERSER_BROKER_URL", default="redis://redis:6379/0")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": env.str("FEDIVERSER_DATABASE_NAME", default="fediverser"),
        "USER": env.str("FEDIVERSER_DATABASE_USER", default="fediverser"),
        "PASSWORD": env.str("FEDIVERSER_DATABASE_PASSWORD"),
        "HOST": env.str("FEDIVERSER_DATABASE_HOST", default="db"),
        "PORT": env.str("FEDIVERSER_DATABASE_PORT", default=5432),
    },
    "lemmy": {
        "ENGINE": env.str(
            "LEMMY_DATABASE_ENGINE", default="django.db.backends.postgresql_psycopg2"
        ),
        "NAME": env.str("LEMMY_DATABASE_NAME", default="lemmy"),
        "USER": env.str("LEMMY_DATABASE_USER", default="lemmy"),
        "PASSWORD": env.str("LEMMY_DATABASE_PASSWORD", default=None),
        "HOST": env.str("LEMMY_DATABASE_HOST", default="lemmy-db"),
        "PORT": env.str("LEMMY_DATABASE_PORT", default=5432),
    },
}
DATABASE_ROUTERS = ("fediverser.admin.database_router.InternalRouter",)

# Authentication and Account Management
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
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
        "django.db.backends:": {
            "handlers": LOGGING_HANDLER_METHODS,
            "level": "ERROR",
            "propagate": False,
        },
        "django.request": {
            "handlers": LOGGING_HANDLER_METHODS,
            "level": "ERROR",
            "propagate": False,
        },
    },
}


for app in INTERNAL_APPS:
    LOGGING["loggers"][app] = {
        "handlers": LOGGING_HANDLER_METHODS,
        "level": LOG_LEVEL,
        "propagate": False,
    }


# Reddit
REDDIT_CLIENT_ID = env.str("FEDIVERSER_REDDIT_CLIENT_ID", default=None)
REDDIT_CLIENT_SECRET = env.str("FEDIVERSER_REDDIT_CLIENT_SECRET", default=None)
REDDIT_USER_AGENT = env.str("FEDIVERSER_REDDIT_USER_AGENT", default="fediverser/0.1.0")
REDDIT_BOT_ACCOUNT_USERNAME = env.str("REDDIT_BOT_ACCOUNT_USERNAME", default=None)
REDDIT_BOT_ACCOUNT_PASSWORD = env.str("REDDIT_BOT_ACCOUNT_PASSWORD", default=None)

# Lemmy

LEMMY_MIRROR_INSTANCE_DOMAIN = env.str("FEDIVERSER_LEMMY_MIRROR_INSTANCE", default=None)
