"""
Test Email Verification System (V2.8)

Django Best Practice: Test token validation, expiration, user activation,
and transaction atomicity.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from apps.users.models import EmailVerification

User = get_user_model()


class EmailVerificationModelTests(TestCase):
    """Test EmailVerification model methods."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            email="verify@example.com",
            password="TestPassword123!",
            is_active=False,
            email_verified=False,
        )

    def test_token_auto_generated(self):
        """Test verification token is automatically generated as UUID."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertIsNotNone(verification.token)
        # UUID4 format check
        token_str = str(verification.token)
        self.assertEqual(len(token_str), 36)  # UUID4 length with hyphens

    def test_is_expired_false_for_new_token(self):
        """Test is_expired() returns False for new token."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertFalse(verification.is_expired())

    def test_is_expired_true_after_24_hours(self):
        """Test is_expired() returns True after 24 hours."""
        verification = EmailVerification.objects.create(user=self.user)

        # Manually set created_at to 25 hours ago
        verification.created_at = timezone.now() - timedelta(hours=25)
        verification.save()

        self.assertTrue(verification.is_expired())

    def test_is_verified_false_initially(self):
        """Test is_verified() returns False for new verification."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertFalse(verification.is_verified())
        self.assertIsNone(verification.verified_at)

    def test_is_verified_true_after_verification(self):
        """Test is_verified() returns True after calling verify()."""
        verification = EmailVerification.objects.create(user=self.user)

        result = verification.verify()

        self.assertTrue(result)
        self.assertTrue(verification.is_verified())
        self.assertIsNotNone(verification.verified_at)

    def test_verify_activates_user(self):
        """Test verify() activates user and sets email_verified."""
        verification = EmailVerification.objects.create(user=self.user)

        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.email_verified)

        verification.verify()
        self.user.refresh_from_db()

        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.email_verified)

    def test_verify_expired_token_fails(self):
        """Test verify() returns False for expired token."""
        verification = EmailVerification.objects.create(user=self.user)

        # Set token as expired
        verification.created_at = timezone.now() - timedelta(hours=25)
        verification.save()

        result = verification.verify()

        self.assertFalse(result)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_verify_already_verified_token(self):
        """Test verify() handles already verified token gracefully."""
        verification = EmailVerification.objects.create(user=self.user)

        # First verification
        first_result = verification.verify()
        first_verified_at = verification.verified_at

        # Second verification attempt
        second_result = verification.verify()

        self.assertTrue(first_result)  # First should succeed
        self.assertFalse(second_result)  # Second should return False (already verified)
        # verified_at should not change
        self.assertEqual(verification.verified_at, first_verified_at)

    def test_one_verification_per_user(self):
        """Test OneToOne relationship enforces single verification per user."""
        EmailVerification.objects.create(user=self.user)

        # Attempting to create another should fail
        with self.assertRaises(Exception):
            EmailVerification.objects.create(user=self.user)


class VerifyEmailViewTests(TestCase):
    """Test VerifyEmailView endpoint."""

    def setUp(self):
        """Set up test client and create test user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="verify@example.com",
            password="TestPassword123!",
            is_active=False,
            email_verified=False,
        )
        self.verification = EmailVerification.objects.create(user=self.user)
        self.url = reverse("verify-email")

    @patch("users.views_verification.log_action")
    def test_verify_email_success(self, mock_log_action):
        """Test successful email verification."""
        url_with_token = f"{self.url}?token={self.verification.token}"

        response = self.client.get(url_with_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertIn("user", response.data)

        # Verify user is now active
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.email_verified)

        # Verify audit log
        mock_log_action.assert_called_once()

    def test_verify_email_missing_token(self):
        """Test verification fails when token is missing."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_verify_email_invalid_token(self):
        """Test verification fails with invalid token."""
        url_with_token = f"{self.url}?token=invalid-token-12345"

        response = self.client.get(url_with_token)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_verify_email_expired_token(self):
        """Test verification fails with expired token."""
        # Expire the token
        self.verification.created_at = timezone.now() - timedelta(hours=25)
        self.verification.save()

        url_with_token = f"{self.url}?token={self.verification.token}"

        response = self.client.get(url_with_token)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", response.data["error"].lower())

    def test_verify_email_already_verified(self):
        """Test verification handles already verified email."""
        # Verify once
        self.verification.verify()

        url_with_token = f"{self.url}?token={self.verification.token}"

        response = self.client.get(url_with_token)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already verified", response.data["message"].lower())

    def test_verify_email_public_endpoint(self):
        """Test verify email endpoint is accessible without authentication."""
        url_with_token = f"{self.url}?token={self.verification.token}"

        response = self.client.get(url_with_token)

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ResendVerificationViewTests(TestCase):
    """Test ResendVerificationView endpoint."""

    def setUp(self):
        """Set up test client and create test user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="resend@example.com",
            password="TestPassword123!",
            is_active=False,
            email_verified=False,
        )
        self.url = reverse("resend-verification")

    @patch("users.tasks.send_verification_email.delay")
    def test_resend_verification_success(self, mock_send_email):
        """Test successful resend of verification email."""
        # Delete any existing verification to avoid IntegrityError
        EmailVerification.objects.filter(user=self.user).delete()

        data = {"email": "resend@example.com"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

        # Verify verification record created
        verification = EmailVerification.objects.filter(user=self.user).first()
        self.assertIsNotNone(verification)

        # Verify email task called
        mock_send_email.assert_called_once()

    @patch("users.tasks.send_verification_email.delay")
    def test_resend_verification_reuses_valid_token(self, mock_send_email):
        """Test resend reuses existing valid token instead of creating new one."""
        # Create existing verification
        existing_verification = EmailVerification.objects.create(user=self.user)
        existing_token = existing_verification.token

        data = {"email": "resend@example.com"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify same token is reused
        verification = EmailVerification.objects.get(user=self.user)
        self.assertEqual(verification.token, existing_token)

    @patch("users.tasks.send_verification_email.delay")
    def test_resend_verification_creates_new_token_if_expired(self, mock_send_email):
        """Test resend creates new token if existing one is expired."""
        # Create expired verification
        old_verification = EmailVerification.objects.create(user=self.user)
        old_verification.created_at = timezone.now() - timedelta(hours=25)
        old_verification.save()
        old_token = old_verification.token

        data = {"email": "resend@example.com"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify new token created
        verification = EmailVerification.objects.get(user=self.user)
        self.assertNotEqual(verification.token, old_token)

    def test_resend_verification_already_verified(self):
        """Test resend for already verified user."""
        # Mark user as verified
        self.user.is_active = True
        self.user.email_verified = True
        self.user.save()

        data = {"email": "resend@example.com"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already verified", response.data["message"].lower())

    def test_resend_verification_user_not_found(self):
        """Test resend doesn't reveal if user exists."""
        data = {"email": "nonexistent@example.com"}

        response = self.client.post(self.url, data, format="json")

        # Should return 200 to not reveal user existence
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_resend_verification_missing_email(self):
        """Test resend fails when email is missing."""
        data = {}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_resend_verification_invalid_email_format(self):
        """Test resend handles invalid email format."""
        data = {"email": "not-an-email"}

        response = self.client.post(self.url, data, format="json")

        # Email validation should pass through Django email field validation
        # Response should still be generic for security
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_resend_verification_public_endpoint(self):
        """Test resend verification endpoint is accessible without authentication."""
        # Use a different email to avoid OneToOne constraint conflict
        data = {"email": "different@example.com"}

        response = self.client.post(self.url, data, format="json")

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("users.tasks.send_verification_email.delay")
    def test_resend_verification_normalizes_email(self, mock_send_email):
        """Test resend normalizes email (case insensitive)."""
        # Delete any existing verification to avoid IntegrityError
        EmailVerification.objects.filter(user=self.user).delete()

        data = {"email": "RESEND@EXAMPLE.COM"}

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Should find user despite case difference
        mock_send_email.assert_called_once()
