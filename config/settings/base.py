import os
import sys
import environ
from django.utils.translation import gettext_lazy as _
from config.env import BASE_DIR

# Import UNFOLD before Django apps to ensure proper initialization
from ..scripts.unfold import UNFOLD

# Initialize environ
env = environ.Env()

# Read .env file
env.read_env(os.path.join(BASE_DIR, ".env"))

# Add apps to Python path
sys.path.insert(0, os.path.join(BASE_DIR, "apps"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("DJANGO_SECRET_KEY")


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])


# Application definition
DJANGO_APPS = [
    "unfold",  # before django.contrib.admin
    "axes",
    "django.contrib.admin",  # required
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_filters",
]

CUSTOM_APPS = [
    "users.apps.UsersConfig",
    "audit",
    "common",
    "households",
    "organisations",
    "accounts",
    "transactions",
    "categories",
    "budgets",
    "goals",
    "bills",
    "rewards",
    "alerts",
    "lessons",
    "reports",
    "privacy",
    # "apps.ml",  # Temporarily disabled - requires clean venv with proper numpy/statsmodels
]

THIRD_PARTY_APPS = [
    "boto3",
    "storages",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_celery_results",
]

INSTALLED_APPS = DJANGO_APPS + CUSTOM_APPS + THIRD_PARTY_APPS 

AUTHENTICATION_BACKENDS = [
    "apps.users.backends.EmailOrUsernameBackend",  # Custom backend: email or username
    "axes.backends.AxesStandaloneBackend",  # Axes for brute-force protection
    "django.contrib.auth.backends.ModelBackend",  # Default fallback
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Static files - must be after SecurityMiddleware
    "config.middleware.security.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",  # CORS - must be before CommonMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",  # ← Moved up
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "axes.middleware.AxesMiddleware",
    "config.middleware.request_timeout.RequestTimeoutMiddleware",  # Track request duration
    "config.middleware.request_timeout.RequestSizeLimitMiddleware",  # Enforce size limits
    "config.middleware.request_signing.RequestSigningMiddleware",  # Verify request signatures
    "config.middleware.csp_custom.CustomCSPMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "config.middleware.security.CookieSecurityMiddleware",
    #
    "config.middleware.session.IdleTimeoutMiddleware",  # Updated class name
    #
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "config.utils.ratelimit.AdminLoginRateLimitMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Ensure this line is added
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.session_timeout",  # Idle timeout values
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,  # SOC 2 compliance recommendation
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "Pacific/Auckland"

USE_I18N = True

USE_TZ = True

# Supported languages
LANGUAGES = [
    ("en", "English"),
    ("en-nz", "English (New Zealand)"),
    ("en-au", "English (Australia)"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Media files (User uploads)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Media files (User uploads)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": env("AWS_S3_BUCKET_NAME", default=""),
            "region_name": env("AWS_REGION", default="ap-southeast-2"),
            "access_key": env("AWS_ACCESS_KEY_ID", default=""),
            "secret_key": env("AWS_SECRET_ACCESS_KEY", default=""),
            "custom_domain": f"{env('AWS_S3_BUCKET_NAME', default='')}.s3.amazonaws.com",
            "location": "media",
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
        "OPTIONS": {
            "bucket_name": env("AWS_S3_BUCKET_NAME", default=""),
            "region_name": env("AWS_REGION", default="ap-southeast-2"),
            "access_key": env("AWS_ACCESS_KEY_ID", default=""),
            "secret_key": env("AWS_SECRET_ACCESS_KEY", default=""),
            "custom_domain": f"{env('AWS_S3_BUCKET_NAME', default='')}.s3.amazonaws.com",
            "location": "static",
        },
    }
}



# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom User model
AUTH_USER_MODEL = "users.User"

# Login/Logout URLs
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"

# Session Configuration
SESSION_SAVE_EVERY_REQUEST = True  # Required for idle timeout to track activity

# Idle Timeout Configuration
IDLE_TIMEOUT_SECONDS = 15 * 60  # 15 minutes of inactivity
IDLE_GRACE_SECONDS = 2 * 60  # 2 minutes grace period

# Email Configuration
# https://docs.djangoproject.com/en/5.2/topics/email/
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@kinwise.com")
SERVER_EMAIL = env("SERVER_EMAIL", default="errors@kinwise.com")

# Admin and Manager emails for error reporting
ADMINS = [("Admin", env("ADMIN_EMAIL", default="admin@kinwise.com"))]
MANAGERS = ADMINS

# Data Upload Limits
# https://docs.djangoproject.com/en/5.2/ref/settings/#data-upload-max-memory-size
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Explicit imports instead of wildcard imports (Django best practice)
# Security Settings
from config.security import (
    SECURE_SSL_REDIRECT,
    SESSION_COOKIE_SECURE,
    CSRF_COOKIE_SECURE,
    SESSION_COOKIE_HTTPONLY,
    CSRF_COOKIE_HTTPONLY,
    SECURE_HSTS_SECONDS,
    SECURE_HSTS_INCLUDE_SUBDOMAINS,
    SECURE_HSTS_PRELOAD,
    SECURE_CONTENT_TYPE_NOSNIFF,
    REFERRER_POLICY,
    AXES_LOCKOUT_PARAMETERS,
    AXES_FAILURE_LIMIT,
    AXES_COOLOFF_TIME,
    AXES_LOCK_OUT_AT_FAILURE,
    AXES_RESET_ON_SUCCESS,
    AXES_ENABLED,
    SESSION_COOKIE_AGE,
)

# Logging Configuration
from config.addon.logging import LOGGING  # noqa: F401

# CORS Configuration
from config.addon.cors import (
    CORS_ALLOWED_ORIGINS,
    CORS_ALLOW_CREDENTIALS,
    CORS_ALLOW_METHODS,
    CORS_ALLOW_HEADERS,
    CORS_EXPOSE_HEADERS,
    CORS_PREFLIGHT_MAX_AGE,
)

# Content Security Policy Configuration
from config.addon.csp import (
    CSP_DEFAULT_SRC,
    CSP_SCRIPT_SRC,
    CSP_STYLE_SRC,
    CSP_IMG_SRC,
    CSP_FONT_SRC,
    CSP_CONNECT_SRC,
    CSP_FRAME_ANCESTORS,
    CSP_BASE_URI,
    CSP_FORM_ACTION,
    CSP_OBJECT_SRC,
    CSP_MANIFEST_SRC,
    CSP_INCLUDE_NONCE_IN,
    CSP_EXCLUDE_URL_PREFIXES,
)

# Cache Configuration
from config.addon.cache import (
    CACHES,
    RATELIMIT_ENABLE,
    RATELIMIT_USE_CACHE,
    SESSION_ENGINE,
    SESSION_CACHE_ALIAS,
)

# JWT Configuration
from config.addon.simple_jwt import SIMPLE_JWT  # noqa: F401

# REST Framework Configuration
from config.addon.rest_framework import REST_FRAMEWORK  # noqa: F401

# API Documentation Configuration
from config.addon.drf_spectacular import SPECTACULAR_SETTINGS  # noqa: F401

# ==============================================================================
# CELERY CONFIGURATION
# ==============================================================================

# Broker settings (Redis)
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")

# Task settings
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit

# Result backend settings
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour
CELERY_RESULT_PERSISTENT = True

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# Beat schedule (django-celery-beat)
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Task routes (organize by app)
CELERY_TASK_ROUTES = {
    "users.tasks.*": {"queue": "users"},
    "bills.tasks.*": {"queue": "bills"},
    "goals.tasks.*": {"queue": "goals"},
}

# Frontend URL (for email verification links)
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# ==============================================================================
# API SECURITY - REQUEST SIGNING & TIMEOUTS
# ==============================================================================

# Generate key with: python -c "import secrets; print(secrets.token_hex(32))"
API_SIGNING_KEY = env("API_SIGNING_KEY", default=None)

# Enable request signing verification on sensitive endpoints
# Set to True in production, False for development
API_REQUEST_SIGNING_ENABLED = env.bool("API_REQUEST_SIGNING_ENABLED", default=False)

# Request timeout enforcement
REQUEST_TIMEOUT_SECONDS = env.int("REQUEST_TIMEOUT_SECONDS", default=30)
SLOW_REQUEST_THRESHOLD_SECONDS = env.int("SLOW_REQUEST_THRESHOLD_SECONDS", default=10)
TIMEOUT_EXEMPT_PATHS = [
    "/health/",
    "/status/",
    "/api/v1/auth/login/",  # Auth endpoint may be slower
]

# Request size limits
MAX_REQUEST_SIZE_MB = env.int("MAX_REQUEST_SIZE_MB", default=10)
MAX_JSON_BODY_SIZE = env.int("MAX_JSON_BODY_SIZE", default=1048576)  # 1MB

# ==============================================================================

from config.addon.aws import *  # noqa: F401, F403