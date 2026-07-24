"""
Base Django settings for DeviceFlow.
"""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)

environ.Env.read_env(ROOT_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-insecure-change-me-deviceflow-phase1")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "channels",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.common.apps.CommonConfig",
    "apps.accounts",
    "apps.tenants",
    "apps.projects",
    "apps.devices",
    "apps.messaging",
    "apps.routing",
    "apps.webhooks",
    "apps.contacts",
    "apps.audit",
    "apps.realtime",
    "apps.analytics",
    "apps.plugins",
    "apps.notifications",
    "apps.automations",
    "apps.ai",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# SQLite under uvicorn + agent heartbeats needs a longer busy wait; WAL is
# enabled in apps.common.apps via connection_created.
_db_engine = str(DATABASES["default"].get("ENGINE", ""))
if "sqlite" in _db_engine:
    DATABASES["default"].setdefault("OPTIONS", {})
    DATABASES["default"]["OPTIONS"].setdefault("timeout", 30)


AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEVICEFLOW_PLUGINS_DIRS = [
    str(BASE_DIR / "plugins"),
    str(ROOT_DIR / "plugins"),
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "apps.projects.authentication.ApiKeyAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "apps.common.permissions.IsAuthenticatedOrApiKey",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DeviceFlow API",
    "DESCRIPTION": "Enterprise SMS gateway API — JWT or API key auth.",
    "VERSION": "0.7.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

SIMPLE_JWT = {
    # Access is short-lived; dashboard auto-refreshes via /auth/refresh/.
    "ACCESS_TOKEN_LIFETIME": timedelta(
        minutes=env.int("JWT_ACCESS_MINUTES", default=720)
    ),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=30)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
)
CORS_ALLOW_CREDENTIALS = True

CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "mark-stale-devices-offline": {
        "task": "devices.mark_stale_devices_offline",
        "schedule": 30.0,
    },
    "refresh-health-scores": {
        "task": "devices.refresh_health_scores",
        "schedule": 300.0,
    },
    "reset-sim-daily-sent": {
        "task": "devices.reset_sim_daily_sent",
        "schedule": timedelta(hours=24),
    },
    "analytics-rollup-hourly": {
        "task": "analytics.rollup_hourly",
        "schedule": timedelta(hours=1),
    },
    "ai-scan-anomalies": {
        "task": "ai.scan_anomalies",
        "schedule": 300.0,
    },
    "messaging-promote-retries": {
        "task": "messaging.promote_retries",
        "schedule": 15.0,
    },
    "messaging-promote-scheduled": {
        "task": "messaging.promote_scheduled",
        "schedule": 15.0,
    },
}

OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o-mini")

# Channels: use in-memory for local/dev when Redis is unavailable; Redis in compose/prod.
CHANNEL_LAYERS = {
    "default": (
        {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [env("REDIS_URL", default="redis://localhost:6379/0")]},
        }
        if env.bool("CHANNELS_USE_REDIS", default=False)
        else {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    )
}

DEVICE_OFFLINE_AFTER_SECONDS = env.int("DEVICE_OFFLINE_AFTER_SECONDS", default=45)
