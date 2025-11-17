from .base import *  # noqa
from config import env  # noqa
import dj_database_url

DEBUG = False

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Database with connection pooling for production
# https://docs.djangoproject.com/en/5.2/ref/databases/#persistent-connections
if env("DATABASE_URL", default=None):
    DATABASES = {
        "default": {
            **dj_database_url.parse(env("DATABASE_URL")),
            "CONN_MAX_AGE": 600,  # 10 minutes persistent connections
            "CONN_HEALTH_CHECKS": True,  # Enable connection health checks
            "OPTIONS": {
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000",  # 30 seconds query timeout
            },
            "ATOMIC_REQUESTS": True,  # Wrap each request in transaction
        }
    }


# Redis caches for production
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "kinwise-prod",
        "TIMEOUT": 300,
    },
    "ratelimit": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL_RATELIMIT"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "ratelimit-prod",
        "TIMEOUT": 3600,
    },
}

# Rate limiting
RATELIMIT_CACHE = "ratelimit"
