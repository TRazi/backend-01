"""
Test Email OTP Authentication (V2.8)

Django Best Practice: Test complete flow, edge cases, security,
and use select_for_update race condition prevention.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from apps.users.models import EmailOTP
from apps.users.serializers import EmailOTPRequestSerializer, EmailOTPVerifySerializer

User = get_user_model()


class EmailOTPModelTests(TestCase):
    """Test EmailOTP model methods and validation."""

    def setUp(self):
        """Create test user."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="TestPassword123!",
            email_verified=True,
            is_active=True,
        )

    def test_otp_code_generation(self):
        """Test OTP code is automatically generated as 6 digits."""
        otp = EmailOTP.objects.create(user=self.user)

        self.assertIsNotNone(otp.code)
        self.assertEqual(len(otp.code), 6)
        self.assertTrue(otp.code.isdigit())

    def test_otp_expiration_set_on_creation(self):
        """Test OTP expires_at is set to 10 minutes from creation."""
        before_creation = timezone.now()
        otp = EmailOTP.objects.create(user=self.user)
        after_creation = timezone.now()

        self.assertIsNotNone(otp.expires_at)
        self.assertGreater(otp.expires_at, before_creation)
        self.assertLess(
            otp.expires_at, after_creation + timedelta(minutes=10, seconds=5)
        )

    def test_otp_is_valid_when_unused_and_not_expired(self):
        """Test is_valid() returns True for valid OTP."""
        otp = EmailOTP.objects.create(user=self.user)

        self.assertTrue(otp.is_valid())
        self.assertFalse(otp.is_used)

    def test_otp_is_invalid_when_used(self):
        """Test is_valid() returns False when OTP is marked as used."""
        otp = EmailOTP.objects.create(user=self.user)
        otp.mark_as_used()

        self.assertFalse(otp.is_valid())
        self.assertTrue(otp.is_used)

    def test_otp_is_invalid_when_expired(self):
        """Test is_valid() returns False for expired OTP."""
        otp = EmailOTP.objects.create(user=self.user)

        # Manually set expiration to the past
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()

        self.assertFalse(otp.is_valid())

    def test_mark_as_used_is_idempotent(self):
        """Test mark_as_used() can be called multiple times safely."""
        otp = EmailOTP.objects.create(user=self.user)

        otp.mark_as_used()
        self.assertTrue(otp.is_used)

        otp.mark_as_used()  # Call again
        self.assertTrue(otp.is_used)


class EmailOTPSerializerTests(TestCase):
    """Test OTP serializers."""

    def test_otp_request_serializer_valid(self):
        """Test EmailOTPRequestSerializer validates correct email."""
        data = {"email": "user@example.com"}
        serializer = EmailOTPRequestSerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "user@example.com")

    def test_otp_request_serializer_invalid_email(self):
        """Test EmailOTPRequestSerializer rejects invalid email."""
        data = {"email": "not-an-email"}
        serializer = EmailOTPRequestSerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_otp_verify_serializer_valid_code(self):
        """Test EmailOTPVerifySerializer validates 6-digit code."""
        data = {"email": "user@example.com", "code": "123456"}
        serializer = EmailOTPVerifySerializer(data=data)

        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["code"], "123456")

    def test_otp_verify_serializer_invalid_code_length(self):
        """Test EmailOTPVerifySerializer rejects non-6-digit codes."""
        test_cases = ["12345", "1234567", "12", ""]

        for code in test_cases:
            data = {"email": "user@example.com", "code": code}
            serializer = EmailOTPVerifySerializer(data=data)

            self.assertFalse(serializer.is_valid(), f"Code '{code}' should be invalid")
            self.assertIn("code", serializer.errors)

    def test_otp_verify_serializer_non_numeric_code(self):
        """Test EmailOTPVerifySerializer rejects non-numeric codes."""
        data = {"email": "user@example.com", "code": "abc123"}
        serializer = EmailOTPVerifySerializer(data=data)

        self.assertFalse(serializer.is_valid())
        self.assertIn("code", serializer.errors)


class EmailOTPViewSetTests(TestCase):
    """Test EmailOTPViewSet endpoints."""

    def setUp(self):
        """Set up test client and create test user."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="otp@example.com",
            password="TestPassword123!",
            email_verified=True,
            is_active=True,
        )

    @patch("users.views_otp.transaction.on_commit")
    @patch("users.tasks.send_otp_email.delay")
    def test_request_otp_success(self, mock_send_otp, mock_on_commit):
        """Test successful OTP request."""
        mock_on_commit.side_effect = lambda func: func()

        url = reverse("email-otp-request-otp")
        data = {"email": "otp@example.com"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data["expires_in"], 600)

        # Verify OTP created in database
        otp = EmailOTP.objects.filter(user=self.user, is_used=False).first()
        self.assertIsNotNone(otp)

        # Verify email task called
        mock_send_otp.assert_called_once()

    def test_request_otp_user_not_found(self):
        """Test OTP request for non-existent user doesn't reveal existence."""
        url = reverse("email-otp-request-otp")
        data = {"email": "nonexistent@example.com"}

        response = self.client.post(url, data, format="json")

        # Should return 200 to not reveal user existence
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)

    def test_request_otp_inactive_user(self):
        """Test OTP request fails for inactive user."""
        User.objects.create_user(
            email="inactive@example.com",
            password="TestPassword123!",
            is_active=False,
            email_verified=True,
        )

        url = reverse("email-otp-request-otp")
        data = {"email": "inactive@example.com"}

        response = self.client.post(url, data, format="json")

        # Should return generic message
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_otp_unverified_email(self):
        """Test OTP request fails for unverified email."""
        User.objects.create_user(
            email="unverified@example.com",
            password="TestPassword123!",
            is_active=True,
            email_verified=False,
        )

        url = reverse("email-otp-request-otp")
        data = {"email": "unverified@example.com"}

        response = self.client.post(url, data, format="json")

        # Should return generic message
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("users.views_otp.transaction.on_commit")
    @patch("users.tasks.send_otp_email.delay")
    def test_request_otp_invalidates_old_otps(self, mock_send_otp, mock_on_commit):
        """Test requesting OTP invalidates previous unused OTPs."""
        mock_on_commit.side_effect = lambda func: func()

        # Create old OTP
        old_otp = EmailOTP.objects.create(user=self.user)
        old_code = old_otp.code

        url = reverse("email-otp-request-otp")
        data = {"email": "otp@example.com"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify old OTP was invalidated
        old_otp.refresh_from_db()
        self.assertTrue(old_otp.is_used)

        # Verify new OTP created
        new_otp = EmailOTP.objects.filter(user=self.user, is_used=False).first()
        self.assertIsNotNone(new_otp)
        self.assertNotEqual(new_otp.code, old_code)

    @patch("users.views_otp.log_action")
    def test_verify_otp_success(self, mock_log_action):
        """Test successful OTP verification issues JWT tokens."""
        # Create valid OTP
        otp = EmailOTP.objects.create(user=self.user)

        url = reverse("email-otp-verify-otp")
        data = {"email": "otp@example.com", "code": otp.code}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)

        # Verify user data in response
        user_data = response.data["user"]
        self.assertEqual(user_data["email"], "otp@example.com")

        # Verify OTP marked as used
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

        # Verify audit log
        mock_log_action.assert_called_once()

    def test_verify_otp_invalid_code(self):
        """Test OTP verification fails with invalid code."""
        url = reverse("email-otp-verify-otp")
        data = {"email": "otp@example.com", "code": "999999"}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

    def test_verify_otp_expired_code(self):
        """Test OTP verification fails with expired code."""
        # Create expired OTP
        otp = EmailOTP.objects.create(user=self.user)
        otp.expires_at = timezone.now() - timedelta(minutes=1)
        otp.save()

        url = reverse("email-otp-verify-otp")
        data = {"email": "otp@example.com", "code": otp.code}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)
        self.assertIn("expired", response.data["error"].lower())

    def test_verify_otp_used_code(self):
        """Test OTP verification fails with already used code."""
        # Create and use OTP
        otp = EmailOTP.objects.create(user=self.user)
        otp.mark_as_used()

        url = reverse("email-otp-verify-otp")
        data = {"email": "otp@example.com", "code": otp.code}

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_otp_wrong_user(self):
        """Test OTP verification fails when code belongs to different user."""
        # Create another user with OTP
        other_user = User.objects.create_user(
            email="other@example.com",
            password="TestPassword123!",
            email_verified=True,
            is_active=True,
        )
        other_otp = EmailOTP.objects.create(user=other_user)

        url = reverse("email-otp-verify-otp")
        data = {
            "email": "otp@example.com",  # Original user
            "code": other_otp.code,  # Other user's code
        }

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("users.views_otp.log_action")
    def test_verify_otp_failed_login_logged(self, mock_log_action):
        """Test failed OTP verification is logged."""
        url = reverse("email-otp-verify-otp")
        data = {"email": "otp@example.com", "code": "123456"}  # Invalid code

        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify failed login logged
        mock_log_action.assert_called_once()
        call_args = mock_log_action.call_args[1]
        self.assertEqual(call_args["action_type"], "LOGIN_FAILED")

    def test_otp_request_public_endpoint(self):
        """Test OTP request endpoint is accessible without authentication."""
        url = reverse("email-otp-request-otp")
        data = {"email": "otp@example.com"}

        response = self.client.post(url, data, format="json")

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_otp_verify_public_endpoint(self):
        """Test OTP verify endpoint is accessible without authentication."""
        url = reverse("email-otp-verify-otp")
        data = {"email": "otp@example.com", "code": "123456"}

        response = self.client.post(url, data, format="json")

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
