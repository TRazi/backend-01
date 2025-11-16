"""
Tests for user signals.
Tests user_logged_in, user_logged_out, and user_login_failed signals.
Uses Django RequestFactory for proper request object creation.
"""

import pytest
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from audit.models import AuditLog, FailedLoginAttempt

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserSignals:
    """Test user authentication signals."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email="test@example.com", password="TestPass123!"
        )

    def test_user_logged_in_creates_audit_log(self):
        """Test user_logged_in signal creates audit log."""
        # Create proper request object
        request = self.factory.post("/admin/login/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 Test Browser"

        # Send signal
        user_logged_in.send(sender=User, request=request, user=self.user)

        # Check audit log was created
        audit_log = AuditLog.objects.filter(user=self.user, action_type="LOGIN").first()

        assert audit_log is not None
        assert audit_log.success is True
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Mozilla/5.0 Test Browser"
        assert audit_log.request_path == "/admin/login/"
        assert "logged in successfully" in audit_log.action_description

    def test_user_logged_in_with_x_forwarded_for(self):
        """Test user_logged_in extracts IP from X-Forwarded-For."""
        # Create request with X-Forwarded-For header
        request = self.factory.post("/admin/login/")
        request.META["HTTP_X_FORWARDED_FOR"] = "203.0.113.1, 198.51.100.1"
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Test Browser"

        # Send signal
        user_logged_in.send(sender=User, request=request, user=self.user)

        # Check IP is from X-Forwarded-For (first IP)
        audit_log = AuditLog.objects.filter(user=self.user, action_type="LOGIN").first()

        assert audit_log.ip_address == "203.0.113.1"

    def test_user_logged_out_creates_audit_log(self):
        """Test user_logged_out signal creates audit log."""
        # Create proper request object
        request = self.factory.post("/admin/logout/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 Test Browser"

        # Send signal
        user_logged_out.send(sender=User, request=request, user=self.user)

        # Check audit log was created
        audit_log = AuditLog.objects.filter(
            user=self.user, action_type="LOGOUT"
        ).first()

        assert audit_log is not None
        assert audit_log.success is True
        assert audit_log.ip_address == "192.168.1.1"
        assert audit_log.user_agent == "Mozilla/5.0 Test Browser"
        assert "logged out" in audit_log.action_description

    def test_user_logged_out_with_none_user(self):
        """Test user_logged_out handles None user gracefully."""
        request = self.factory.post("/admin/logout/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Send signal with None user - should not create audit log
        initial_count = AuditLog.objects.count()
        user_logged_out.send(sender=User, request=request, user=None)

        # No audit log should be created for None user
        assert AuditLog.objects.count() == initial_count

    def test_user_login_failed_creates_audit_log(self):
        """Test user_login_failed signal creates audit log."""
        request = self.factory.post("/admin/login/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 Test Browser"

        credentials = {"username": "test@example.com"}

        # Send signal
        user_login_failed.send(sender=User, credentials=credentials, request=request)

        # Check audit log was created
        audit_log = AuditLog.objects.filter(action_type="LOGIN_FAILED").first()

        assert audit_log is not None
        assert audit_log.user is None  # No user for failed login
        assert audit_log.success is False
        assert audit_log.ip_address == "192.168.1.1"
        assert "Failed login attempt" in audit_log.action_description
        assert audit_log.metadata["username"] == "test@example.com"

    def test_user_login_failed_creates_failed_login_attempt(self):
        """Test user_login_failed signal creates FailedLoginAttempt record."""
        request = self.factory.post("/admin/login/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 Test Browser"

        credentials = {"username": "test@example.com"}

        # Send signal
        user_login_failed.send(sender=User, credentials=credentials, request=request)

        # Check FailedLoginAttempt was created
        attempt = FailedLoginAttempt.objects.filter(username="test@example.com").first()

        assert attempt is not None
        assert attempt.ip_address == "192.168.1.1"
        assert attempt.user_agent == "Mozilla/5.0 Test Browser"
        assert attempt.request_path == "/admin/login/"

    def test_user_login_failed_unknown_username(self):
        """Test user_login_failed handles missing username."""
        request = self.factory.post("/admin/login/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        credentials = {}  # No username

        # Send signal
        user_login_failed.send(sender=User, credentials=credentials, request=request)

        # Check audit log uses "unknown" for missing username
        audit_log = AuditLog.objects.filter(action_type="LOGIN_FAILED").first()

        assert audit_log is not None
        assert "unknown" in audit_log.action_description.lower()
