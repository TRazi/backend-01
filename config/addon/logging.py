import os
from config.settings.base import env

LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "fmt": "%(asctime)s %(levelname)s %(name)s %(message)s %(pathname)s %(lineno)d",
        },
        "simple": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console_json": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console_json"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django.security": {
            "handlers": ["console_json"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console_json"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {  # <- this replaces the plain-text runserver output
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "axes": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
        "kinwise": {
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": True,
        },
        "kinwise.audit": {  # we'll use this next
            "handlers": ["console_json"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
