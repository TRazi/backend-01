"""
Tests for rate limiting functionality.
"""

import pytest
from django.test import TestCase, Client
from django.core.cache import cache, caches


@pytest.mark.django_db
class RateLimitActiveTests(TestCase):
    """Verify rate limiting is configured and active."""

    def setUp(self):
        """Clear cache before test."""
        cache.clear()
        caches["ratelimit"].clear()
        self.client = Client()

    def test_rate_limiting_is_enabled(self):
        """Verify rate limiting is enabled in settings."""
        from django.conf import settings

        self.assertTrue(settings.RATELIMIT_ENABLE)
        self.assertEqual(settings.RATELIMIT_USE_CACHE, "ratelimit")

    def test_rate_limit_cache_works(self):
        """Verify ratelimit cache is functional."""
        rl_cache = caches["ratelimit"]
        rl_cache.set("test_key", "test_value", timeout=60)
        self.assertEqual(rl_cache.get("test_key"), "test_value")

    def test_admin_login_eventually_rate_limits(self):
        """
        Verify that repeated login attempts eventually get rate limited.
        """
        login_url = "/admin/login/"
        rate_limited = False

        # Try up to 10 attempts
        for i in range(10):
            response = self.client.post(
                login_url, {"username": "testuser", "password": "wrongpassword"}
            )

            if response.status_code == 429:
                rate_limited = True
                # Rate limiting kicked in - test passes
                break

        # Assert that rate limiting kicked in at some point
        self.assertTrue(
            rate_limited, "Rate limiting should have been triggered within 10 attempts"
        )
