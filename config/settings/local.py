"""
Local development settings for KinWise v2.
"""

import dj_database_url
from config.env import env
from .base import *  # noqa

# Debug mode for local development
DEBUG = True

# Database - use DATABASE_URL if set, otherwise SQLite
DATABASE_URL = env("DATABASE_URL", default=None)
if DATABASE_URL:
    DATABASES = {"default": dj_database_url.config(default=DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Allowed hosts for local development
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
]

# Email backend - console for local testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS settings for local development
CORS_ALLOW_ALL_ORIGINS = True  # Relaxed for local dev
CORS_ALLOW_CREDENTIALS = True

# Security settings (relaxed for local development)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False
