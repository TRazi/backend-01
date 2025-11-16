"""
Rate limiting middleware for admin login protection.
"""

from django.http import JsonResponse
from django_ratelimit.decorators import ratelimit
from rest_framework import status


class AdminLoginRateLimitMiddleware:
    """
    Middleware to apply rate limiting to admin login without replacing admin site.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Import here to avoid circular imports
        import logging

        logger = logging.getLogger(__name__)

        # Log all admin login requests
        if request.path == "/admin/login/":
            logger.info(
                f"Admin login request: method={request.method}, path={request.path}"
            )

        # Only apply to admin login POST requests
        if request.path == "/admin/login/" and request.method == "POST":
            # Check rate limit
            key = self._get_rate_limit_key(request)

            # Import here to avoid circular imports
            from django.core.cache import caches

            cache = caches["ratelimit"]
            cache_key = f"rl:admin_login:{key}"

            # Get current count
            count = cache.get(cache_key, 0)
            logger.info(f"Rate limit check: key={key}, current count={count}")

            # Increment counter first
            new_count = count + 1
            cache.set(cache_key, new_count, timeout=60)  # 1 minute window
            logger.info(f"Rate limit: incremented to {new_count}")

            # Check if limit exceeded (after incrementing)
            logger.info(f"Checking: {new_count} > 4? Result: {new_count > 4}")
            if new_count > 4:  # Allow 4 attempts, block on 5th
                logger.warning(f"Rate limit exceeded: {new_count} > 4, returning 429")
                return JsonResponse(
                    {
                        "error": "Rate limit exceeded",
                        "detail": "Too many login attempts. Please try again in 1 minute.",
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            logger.info(f"Rate limit OK: {new_count} <= 4, allowing request")

        response = self.get_response(request)
        return response

    def _get_rate_limit_key(self, request):
        """Get rate limit key (IP address)."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
