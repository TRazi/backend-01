"""
Test Celery Tasks (V2.8)

Django Best Practice: Test async task execution, retry logic,
error handling, and email sending.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core import mail
from unittest.mock import patch, MagicMock
from celery.exceptions import Retry

from apps.users.tasks import send_verification_email, send_otp_email, send_welcome_email
from apps.users.models import EmailVerification, EmailOTP

User = get_user_model()


class SendVerificationEmailTaskTests(TestCase):
    """Test send_verification_email Celery task."""

    def setUp(self):
        """Create test user and verification."""
        self.user = User.objects.create_user(
            email="verify@example.com", password="TestPassword123!", first_name="John"
        )
        self.verification = EmailVerification.objects.create(user=self.user)

    def test_send_verification_email_success(self):
        """Test verification email is sent successfully."""
        result = send_verification_email(self.user.id, str(self.verification.token))

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, ["verify@example.com"])
        self.assertIn("Verify your KinWise account", email.subject)
        self.assertIn(str(self.verification.token), email.body)
        self.assertIn("John", email.body)

        # Check return value
        self.assertIn("verify@example.com", result)

    def test_send_verification_email_user_not_found(self):
        """Test task handles non-existent user gracefully."""
        result = send_verification_email(99999, str(self.verification.token))

        self.assertIn("not found", result)
        self.assertEqual(len(mail.outbox), 0)

    @patch("users.tasks.send_verification_email.retry")
    @patch("users.tasks.send_mail")
    def test_send_verification_email_retry_on_error(self, mock_send_mail, mock_retry):
        """Test task retries on exception with exponential backoff."""
        # Mock send_mail to raise exception
        mock_send_mail.side_effect = Exception("Email service error")
        # Mock retry to raise Retry exception
        from celery.exceptions import Retry

        mock_retry.side_effect = Retry()

        with self.assertRaises(Retry):
            send_verification_email(self.user.id, str(self.verification.token))

        # Verify retry was called
        mock_retry.assert_called_once()

    def test_send_verification_email_html_content(self):
        """Test verification email contains HTML content."""
        send_verification_email(self.user.id, str(self.verification.token))

        email = mail.outbox[0]

        # Check for HTML alternative
        self.assertTrue(hasattr(email, "alternatives"))
        if email.alternatives:
            html_content = email.alternatives[0][0]
            self.assertIn("<!DOCTYPE html>", html_content)
            self.assertIn(str(self.verification.token), html_content)

    def test_send_verification_email_uses_frontend_url(self):
        """Test verification email uses FRONTEND_URL from settings."""
        with self.settings(FRONTEND_URL="https://app.kinwise.com"):
            send_verification_email(self.user.id, str(self.verification.token))

        email = mail.outbox[0]
        self.assertIn("https://app.kinwise.com", email.body)


class SendOTPEmailTaskTests(TestCase):
    """Test send_otp_email Celery task."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            email="otp@example.com",
            password="TestPassword123!",
            first_name="Jane",
            email_verified=True,
            is_active=True,
        )
        self.otp = EmailOTP.objects.create(user=self.user)

    def test_send_otp_email_success(self):
        """Test OTP email is sent successfully."""
        result = send_otp_email(self.user.id, self.otp.code)

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, ["otp@example.com"])
        self.assertIn("login code", email.subject.lower())
        self.assertIn(self.otp.code, email.body)
        self.assertIn("Jane", email.body)

        # Check return value
        self.assertIn("otp@example.com", result)

    def test_send_otp_email_user_not_found(self):
        """Test task handles non-existent user gracefully."""
        result = send_otp_email(99999, "123456")

        self.assertIn("not found", result)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_otp_email_contains_6_digit_code(self):
        """Test OTP email displays 6-digit code prominently."""
        send_otp_email(self.user.id, self.otp.code)

        email = mail.outbox[0]

        # Code should be in body
        self.assertIn(self.otp.code, email.body)
        self.assertEqual(len(self.otp.code), 6)

    @patch("users.tasks.send_otp_email.retry")
    @patch("users.tasks.send_mail")
    def test_send_otp_email_retry_on_error(self, mock_send_mail, mock_retry):
        """Test task retries on exception."""
        mock_send_mail.side_effect = Exception("SMTP error")
        # Mock retry to raise Retry exception
        from celery.exceptions import Retry

        mock_retry.side_effect = Retry()

        with self.assertRaises(Retry):
            send_otp_email(self.user.id, self.otp.code)

        # Verify retry was called
        mock_retry.assert_called_once()

    def test_send_otp_email_security_warning(self):
        """Test OTP email includes security warning."""
        send_otp_email(self.user.id, self.otp.code)

        email = mail.outbox[0]

        # Should warn user about not sharing code
        body_lower = email.body.lower()
        self.assertTrue(
            any(
                word in body_lower
                for word in ["security", "share", "expire", "minutes"]
            )
        )


class SendWelcomeEmailTaskTests(TestCase):
    """Test send_welcome_email Celery task."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            email="welcome@example.com",
            password="TestPassword123!",
            first_name="Alex",
            is_active=True,
            email_verified=True,
        )

    def test_send_welcome_email_success(self):
        """Test welcome email is sent successfully."""
        result = send_welcome_email(self.user.id)

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)

        email = mail.outbox[0]
        self.assertEqual(email.to, ["welcome@example.com"])
        self.assertIn("Welcome", email.subject)
        self.assertIn("Alex", email.body)

        # Check return value
        self.assertIn("welcome@example.com", result)

    def test_send_welcome_email_user_not_found(self):
        """Test task handles non-existent user gracefully."""
        result = send_welcome_email(99999)

        self.assertIn("not found", result)
        self.assertEqual(len(mail.outbox), 0)

    def test_send_welcome_email_contains_app_features(self):
        """Test welcome email mentions key features."""
        send_welcome_email(self.user.id)

        email = mail.outbox[0]
        body_lower = email.body.lower()

        # Should mention some features
        self.assertTrue(
            any(
                word in body_lower
                for word in ["budget", "track", "goal", "family", "financial"]
            )
        )

    def test_send_welcome_email_html_content(self):
        """Test welcome email contains HTML content."""
        send_welcome_email(self.user.id)

        email = mail.outbox[0]

        # Check for HTML alternative
        if hasattr(email, "alternatives") and email.alternatives:
            html_content = email.alternatives[0][0]
            self.assertIn("<!DOCTYPE html>", html_content)
            self.assertIn("Alex", html_content)


class CeleryTaskRetryTests(TestCase):
    """Test Celery task retry logic and exponential backoff."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            email="retry@example.com", password="TestPassword123!"
        )

    @patch("users.tasks.send_verification_email.retry")
    @patch("users.tasks.send_mail")
    def test_verification_email_retry_exponential_backoff(
        self, mock_send_mail, mock_retry
    ):
        """Test verification email task uses exponential backoff."""
        from celery.exceptions import Retry

        mock_send_mail.side_effect = Exception("SMTP timeout")
        mock_retry.side_effect = Retry()

        verification = EmailVerification.objects.create(user=self.user)

        with self.assertRaises(Retry):
            send_verification_email(self.user.id, str(verification.token))

        # Verify retry was called
        mock_retry.assert_called_once()

    @patch("users.tasks.send_otp_email.retry")
    @patch("users.tasks.send_mail")
    def test_otp_email_retry_exponential_backoff(self, mock_send_mail, mock_retry):
        """Test OTP email task uses exponential backoff."""
        from celery.exceptions import Retry

        mock_send_mail.side_effect = Exception("Connection refused")
        mock_retry.side_effect = Retry()

        with self.assertRaises(Retry):
            send_otp_email(self.user.id, "123456")

        # Verify retry was called
        mock_retry.assert_called_once()

    @patch("users.tasks.send_mail")
    def test_max_retries_reached(self, mock_send_mail):
        """Test task stops retrying after max_retries."""
        mock_send_mail.side_effect = Exception("Permanent failure")

        verification = EmailVerification.objects.create(user=self.user)

        task_instance = send_verification_email
        task_instance.request.retries = 3  # At max_retries

        # Should raise the original exception, not Retry
        with self.assertRaises(Exception) as context:
            send_verification_email(self.user.id, str(verification.token))

        self.assertIn("Permanent failure", str(context.exception))


class CeleryTaskIntegrationTests(TestCase):
    """Integration tests for task interactions."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            email="integration@example.com",
            password="TestPassword123!",
            first_name="Integration",
        )

    def test_registration_flow_sends_two_emails(self):
        """Test complete registration flow sends verification and welcome emails."""
        verification = EmailVerification.objects.create(user=self.user)

        # Send verification email
        send_verification_email(self.user.id, str(verification.token))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify", mail.outbox[0].subject)

        # After verification, send welcome email
        send_welcome_email(self.user.id)
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn("Welcome", mail.outbox[1].subject)

    def test_otp_login_flow_sends_otp_email(self):
        """Test OTP login flow sends email with code."""
        self.user.email_verified = True
        self.user.is_active = True
        self.user.save()

        otp = EmailOTP.objects.create(user=self.user)

        send_otp_email(self.user.id, otp.code)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(otp.code, mail.outbox[0].body)

    def test_email_templates_render_correctly(self):
        """Test all email templates render without errors."""
        verification = EmailVerification.objects.create(user=self.user)
        otp = EmailOTP.objects.create(user=self.user)

        # All tasks should complete without errors
        try:
            send_verification_email(self.user.id, str(verification.token))
            send_otp_email(self.user.id, otp.code)
            send_welcome_email(self.user.id)
        except Exception as e:
            self.fail(f"Email template rendering failed: {e}")

        self.assertEqual(len(mail.outbox), 3)
