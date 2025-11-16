REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "30/min",  # Session keep-alive endpoint
        "auth": "10/min",  # Authentication endpoints (increased from 5 to 10)
        "token_refresh": "10/min",  # Token refresh endpoint
        "registration": "3/hour",  # User registration
    },
    "EXCEPTION_HANDLER": "config.utils.exception_handlers.custom_exception_handler",
}
