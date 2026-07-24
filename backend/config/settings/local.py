"""Local development settings."""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Eager Celery so local runs work without a worker process by default.
CELERY_TASK_ALWAYS_EAGER = True

# Serve admin/app static files via WhiteNoise without collectstatic on every change.
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True
