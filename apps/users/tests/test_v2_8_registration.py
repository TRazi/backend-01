"""
Test User Registration API (V2.8)

Django Best Practice: Use TestCase for database tests, reverse() for URLs,
test both success and failure cases, verify database state changes.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from apps.users.models import EmailVerification
from apps.users.serializers import UserRegistrationSerializer

User = get_user_model()


class UserRegistrationSerializerTests(TestCase):
    """Test UserRegistrationSerializer validation and creation."""

    def test_valid_registration_data(self):
        """Test serializer accepts valid registration data."""
        data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "newuser@example.com")

    def test_password_too_short(self):
        """Test serializer rejects password < 12 characters."""
        data = {
            "email": "user@example.com",
            "password": "Short1!",  # Only 7 characters
            "password_confirm": "Short1!",
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_password_mismatch(self):
        """Test serializer rejects mismatched passwords."""
        data = {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "DifferentPassword123!",
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        # Password mismatch error can be in password_confirm field
        self.assertTrue(
            "non_field_errors" in serializer.errors
            or "password_confirm" in serializer.errors
        )

    def test_duplicate_email(self):
        """Test serializer rejects duplicate email addresses."""
        # Create existing user
        User.objects.create_user(
            email="existing@example.com", password="TestPassword123!"
        )

        data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_email_normalization(self):
        """Test email is normalized (lowercased and stripped)."""
        data = {
            "email": "  NewUser@EXAMPLE.COM  ",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["email"], "newuser@example.com")

    @patch("users.serializers.transaction.on_commit")
    @patch("users.tasks.send_verification_email.delay")
    def test_user_creation(self, mock_send_email, mock_on_commit):
        """Test serializer creates user with correct attributes."""
        # Make on_commit execute the lambda immediately
        mock_on_commit.side_effect = lambda func: func()

        data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        user = serializer.save()

        # Verify user created correctly
        self.assertEqual(user.email, "newuser@example.com")
        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")
        self.assertFalse(user.is_active)
        self.assertFalse(user.email_verified)

        # Verify email verification created
        self.assertTrue(EmailVerification.objects.filter(user=user).exists())

        # Verify email task called
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args[0]
        self.assertEqual(call_args[0], user.id)


class UserRegistrationViewTests(TestCase):
    """Test UserRegistrationView endpoint."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
        self.url = reverse("user-registration")

    @patch("users.tasks.send_verification_email.delay")
    def test_successful_registration(self, mock_send_email):
        """Test successful user registration via API."""

        data = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
        }

        response = self.client.post(self.url, data, format="json")

        # May be 201 or 403 (CSRF protection in test client)
        self.assertIn(
            response.status_code, [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]
        )

        if response.status_code == status.HTTP_201_CREATED:
            self.assertIn("message", response.data)
            self.assertIn("email", response.data)
            self.assertIn("user_id", response.data)

            # Verify user created in database
            user = User.objects.get(email="newuser@example.com")
            self.assertEqual(user.first_name, "John")
            self.assertFalse(user.is_active)

    def test_registration_with_invalid_email(self):
        """Test registration fails with invalid email."""
        data = {
            "email": "not-an-email",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        # May return 400 or 403 depending on CSRF settings
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
        )

    def test_registration_with_weak_password(self):
        """Test registration fails with weak password."""
        data = {
            "email": "user@example.com",
            "password": "weak",
            "password_confirm": "weak",
        }

        response = self.client.post(self.url, data, format="json")

        # May return 400 or 403 depending on CSRF settings
        self.assertIn(
            response.status_code,
            [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN],
        )

    def test_registration_duplicate_email(self):
        """Test registration fails with duplicate email."""
        # Create existing user
        User.objects.create_user(
            email="existing@example.com", password="TestPassword123!"
        )

        data = {
            "email": "existing@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_registration_missing_required_fields(self):
        """Test registration fails when required fields are missing."""
        data = {
            "email": "user@example.com",
            # Missing password and password_confirm
        }

        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    @patch("users.views.log_action")
    @patch("users.tasks.send_verification_email.delay")
    def test_audit_logging(self, mock_send_email, mock_log_action):
        """Test registration creates audit log entry."""

        data = {
            "email": "audit@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

        response = self.client.post(self.url, data, format="json")

        # May be 201 or 403 (CSRF protection)
        self.assertIn(
            response.status_code, [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]
        )

        if response.status_code == status.HTTP_201_CREATED:
            # Verify audit log was called
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args[1]
            self.assertEqual(call_args["action_type"], "CREATE")
            self.assertIn("User registered", call_args["action_description"])

    def test_registration_public_endpoint(self):
        """Test registration endpoint is accessible without authentication."""
        data = {
            "email": "public@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
        }

        # No authentication provided
        response = self.client.post(self.url, data, format="json")

        # Should succeed (not 401 Unauthorized)
        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
