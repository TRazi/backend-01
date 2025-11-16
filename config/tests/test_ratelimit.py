"""
Tests for rate limiting functionality.
"""

import pytest
from django.test import TestCase, Client, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model


def get_user_model_lazy():
    from django.contrib.auth import get_user_model

    return get_user_model()


User = get_user_model_lazy()


@pytest.mark.django_db
class AdminLoginRateLimitTests(TestCase):
    """Test rate limiting on admin login."""

    def setUp(self):
        """Clear cache before each test to avoid rate limit carryover."""
        self.client = Client()

        # Clear all caches to ensure clean test state
        cache.clear()

        # Also clear ratelimit cache specifically
        from django.core.cache import caches

        rl_cache = caches["ratelimit"]
        rl_cache.clear()

    def tearDown(self):
        """Clear cache after test."""
        cache.clear()
        from django.core.cache import caches

        rl_cache = caches["ratelimit"]
        rl_cache.clear()

    def test_admin_login_rate_limit(self):
        """Test that admin login is rate limited after 4 attempts per minute."""
        login_url = "/admin/login/"

        # Make 4 failed login attempts (should NOT be rate limited)
        for i in range(4):
            print(f"\n=== Test iteration {i} (attempt {i+1}) ===")
            response = self.client.post(
                login_url,
                {
                    "username": f"testuser{i}",  # Different username each time
                    "password": "wrongpassword",
                },
            )
            print(f"Response status code: {response.status_code}")
            if response.status_code == 429:
                print(
                    f"Response content: {response.content.decode() if response.content else 'No content'}"
                )
            # Should return 200 (login form with error) or 302 (redirect)
            # Should NOT be 429
            self.assertIn(
                response.status_code,
                [200, 302],
                f"Attempt {i+1} should not be rate limited, got {response.status_code}",
            )

        # 5th attempt should be rate limited
        response = self.client.post(
            login_url, {"username": "testuser_final", "password": "wrongpassword"}
        )

        # Should return 429 Too Many Requests
        self.assertEqual(
            response.status_code,
            429,
            f"5th attempt should be rate limited, got {response.status_code}",
        )

        # Verify JSON response format
        data = response.json()
        self.assertEqual(data["error"], "Rate limit exceeded")
        self.assertIn("detail", data)
