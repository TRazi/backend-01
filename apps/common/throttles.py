"""
Throttling classes for API rate limiting.

This module provides custom throttle classes for protecting endpoints
from abuse while maintaining good user experience.
"""

from rest_framework.throttling import SimpleRateThrottle


class SessionPingThrottle(SimpleRateThrottle):
    """
    Throttle for session keep-alive endpoint.

    Limits requests to 30 per minute per user to prevent:
    - Session enumeration attacks
    - DoS attacks on session validation
    - Excessive server load from automated keep-alive scripts

    Rate: 30 requests per minute (configured in settings.REST_FRAMEWORK)
    Scope: 'session_ping'
    """

    scope = "session_ping"

    def get_cache_key(self, request, view):
        """
        Generate cache key based on user ID (if authenticated) or IP address.

        This ensures authenticated users are throttled per-user, while
        unauthenticated requests are throttled per-IP.
        """
        if request.user and request.user.is_authenticated:
            # Throttle by user ID for authenticated requests
            ident = request.user.id
        else:
            # Throttle by IP for unauthenticated requests
            ident = self.get_ident(request)

        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }
