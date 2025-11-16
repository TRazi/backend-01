"""
Cache configuration for rate limiting and session management.
Follows KinWise v2 addon pattern.

Development: Uses in-memory cache (no Redis required)
Production: Uses Redis (override in production.py)

See: https://docs.djangoproject.com/en/5.2/topics/cache/
"""

from config.env import env

# Cache backend constants
LOCMEM_CACHE_BACKEND = "django.core.cache.backends.locmem.LocMemCache"

# Default to in-memory cache for development
# Production settings will override this with Redis
CACHES = {
    "default": {
        "BACKEND": LOCMEM_CACHE_BACKEND,
        "LOCATION": "kinwise-cache",
        "KEY_PREFIX": "kinwise",
        "VERSION": 1,
        "TIMEOUT": 300,  # 5 minutes default
        "OPTIONS": {
            "MAX_ENTRIES": 1000,
        },
    },
    "ratelimit": {
        "BACKEND": LOCMEM_CACHE_BACKEND,
        "LOCATION": "kinwise-ratelimit",
        "KEY_PREFIX": "ratelimit",
        "TIMEOUT": 3600,  # 1 hour
    },
    "sessions": {
        "BACKEND": LOCMEM_CACHE_BACKEND,
        "LOCATION": "kinwise-sessions",
        "KEY_PREFIX": "session",
        "TIMEOUT": 86400,  # 24 hours
    },
}

# Rate limiting configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "ratelimit"

# Use cached sessions for better performance
# https://docs.djangoproject.com/en/5.2/topics/http/sessions/#using-cached-sessions
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_CACHE_ALIAS = "sessions"
