"""
Tests for idle timeout session middleware.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from django.contrib.sessions.middleware import SessionMiddleware
from config.middleware.session import IdleTimeoutMiddleware
from datetime import timedelta

User = get_user_model()


@pytest.mark.django_db
class TestIdleTimeoutMiddleware(TestCase):
    """Test idle timeout middleware behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

    def get_response_dummy(self, request):
        """Dummy get_response callable."""
        from django.http import HttpResponse

        return HttpResponse("OK")

    def add_session_to_request(self, request):
        """Add session middleware to request."""
        middleware = SessionMiddleware(self.get_response_dummy)
        middleware.process_request(request)
        request.session.save()

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_middleware_disabled_when_timeout_zero(self):
        """Middleware does nothing when timeout is 0."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user

        with override_settings(IDLE_TIMEOUT_SECONDS=0):
            middleware = IdleTimeoutMiddleware(self.get_response_dummy)
            response = middleware.process_request(request)

            self.assertIsNone(response)
            self.assertNotIn("last_activity", request.session)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_static_requests_ignored(self):
        """Static file requests bypass middleware."""
        request = self.factory.get("/static/css/style.css")
        self.add_session_to_request(request)
        request.user = self.user

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)

    @override_settings(
        IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60, LOGIN_URL="/admin/login/"
    )
    def test_login_url_requests_ignored(self):
        """Login URL requests bypass middleware."""
        request = self.factory.get("/admin/login/")
        self.add_session_to_request(request)
        request.user = self.user

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_unauthenticated_user_ignored(self):
        """Unauthenticated users bypass middleware."""
        from django.contrib.auth.models import AnonymousUser

        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = AnonymousUser()

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_first_touch_seeds_last_activity(self):
        """First request seeds last_activity timestamp."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)
        self.assertIn("last_activity", request.session)
        self.assertEqual(request._idle_remaining, 300)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_invalid_timestamp_resets_session(self):
        """Invalid timestamp in session gets reset."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user
        request.session["last_activity"] = "invalid-timestamp"

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)
        self.assertIn("last_activity", request.session)
        # Should have reset
        self.assertEqual(request._idle_remaining, 300)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_hard_expiry_api_request(self):
        """Expired session returns 401 for API requests."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user

        # Set last activity to 400 seconds ago (beyond timeout+grace)
        past_time = timezone.now() - timedelta(seconds=400)
        request.session["last_activity"] = past_time.isoformat()

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 401)
        self.assertIn("session_expired", response.content.decode())

    @override_settings(
        IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60, LOGIN_URL="/login/"
    )
    def test_hard_expiry_html_request(self):
        """Expired session redirects HTML requests to login."""
        request = self.factory.get("/dashboard/")
        self.add_session_to_request(request)
        request.user = self.user

        # Set last activity to 400 seconds ago (beyond timeout+grace)
        past_time = timezone.now() - timedelta(seconds=400)
        request.session["last_activity"] = past_time.isoformat()

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_grace_window_keepalive_extends_session(self):
        """POST to /session/ping/ extends session during grace period."""
        request = self.factory.post("/session/ping/")
        self.add_session_to_request(request)
        request.user = self.user

        # Set last activity to 320 seconds ago (in grace window)
        past_time = timezone.now() - timedelta(seconds=320)
        request.session["last_activity"] = past_time.isoformat()

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)
        self.assertEqual(request._idle_remaining, 300)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_grace_window_non_keepalive_not_extended(self):
        """Non-keepalive requests in grace window don't extend session."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user

        # Set last activity to 320 seconds ago (in grace window)
        past_time = timezone.now() - timedelta(seconds=320)
        request.session["last_activity"] = past_time.isoformat()

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)
        # Should show remaining time until hard expiry
        self.assertLess(request._idle_remaining, 60)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_idle_window_extends_session(self):
        """Activity within idle window extends session."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user

        # Set last activity to 100 seconds ago (within idle window)
        past_time = timezone.now() - timedelta(seconds=100)
        old_timestamp = past_time.isoformat()
        request.session["last_activity"] = old_timestamp

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = middleware.process_request(request)

        self.assertIsNone(response)
        # Session should be extended
        self.assertNotEqual(request.session["last_activity"], old_timestamp)

    @override_settings(IDLE_TIMEOUT_SECONDS=300, IDLE_GRACE_SECONDS=60)
    def test_process_response_adds_headers(self):
        """Response includes session timeout headers."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user
        request._idle_remaining = 250

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = self.get_response_dummy(request)
        response = middleware.process_response(request, response)

        self.assertEqual(response["X-Session-Timeout"], "300")
        self.assertEqual(response["X-Session-Grace"], "60")
        self.assertEqual(response["X-Session-Remaining"], "250")

    @override_settings(IDLE_TIMEOUT_SECONDS=0)
    def test_process_response_no_headers_when_disabled(self):
        """No headers when timeout is disabled."""
        request = self.factory.get("/api/test/")
        self.add_session_to_request(request)
        request.user = self.user

        middleware = IdleTimeoutMiddleware(self.get_response_dummy)
        response = self.get_response_dummy(request)
        response = middleware.process_response(request, response)

        self.assertNotIn("X-Session-Timeout", response)
