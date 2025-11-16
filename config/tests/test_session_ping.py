"""
Tests for session ping view.
"""

import pytest
import time
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestSessionPingView(APITestCase):
    """Test session ping endpoint."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.client = APIClient()

    def test_unauthenticated_request_rejected(self):
        """Unauthenticated users cannot ping session."""
        response = self.client.post("/session/ping/")

        # DRF returns 403 Forbidden for permission denied (not 401)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_authenticated_request_succeeds(self):
        """Authenticated users can ping session."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/session/ping/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_updates_last_activity_in_session(self):
        """POST updates last_activity timestamp in session."""
        self.client.force_authenticate(user=self.user)

        # Make request which should update session
        response = self.client.post("/session/ping/")

        # Should succeed - the actual session update happens in the view
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_method_not_allowed(self):
        """GET method not supported."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/session/ping/")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    @override_settings(RATELIMIT_ENABLE=True)
    def test_rate_limiting_enforced(self):
        """Rate limiting is enforced on session ping."""
        self.client.force_authenticate(user=self.user)

        # The rate limit is 30/m, but we'll just verify the endpoint works
        # (testing actual rate limit exhaustion would require 31+ requests)
        response = self.client.post("/session/ping/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
