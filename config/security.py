# config/security.py
import os
import sys

_DEBUG_FOR_SECURITY = os.environ.get("DJANGO_DEBUG", "False").lower() in (
    "1",
    "true",
    "yes",
)

SECURE_SSL_REDIRECT = not _DEBUG_FOR_SECURITY
SESSION_COOKIE_SECURE = not _DEBUG_FOR_SECURITY
CSRF_COOKIE_SECURE = not _DEBUG_FOR_SECURITY

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
REFERRER_POLICY = "strict-origin-when-cross-origin"

# ---- Axes ----

AXES_LOCKOUT_PARAMETERS = ["username", "ip_address"]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCK_OUT_AT_FAILURE = True
AXES_RESET_ON_SUCCESS = True

# Default: Axes ON
AXES_ENABLED = True

# But if we're running the dev server in DEBUG, turn it off
if _DEBUG_FOR_SECURITY and "runserver" in sys.argv:
    AXES_ENABLED = False

# Session configuration
SESSION_COOKIE_AGE = 60 * 60 * 8  # Hard max 8 hours
SESSION_SAVE_EVERY_REQUEST = True
