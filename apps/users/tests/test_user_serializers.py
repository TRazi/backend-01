"""
Tests for user serializers.
Tests UserSerializer, MFATokenObtainPairSerializer, MFABeginSetupSerializer,
MFAConfirmSetupSerializer, and MFABackupCodeVerifySerializer.
"""

import pytest
from unittest.mock import patch, MagicMock
from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model

from users.serializers import UserSerializer
from users.serializers_auth import MFATokenObtainPairSerializer
from users.serializers_mfa import (
    MFABeginSetupSerializer,
    MFAConfirmSetupSerializer,
    MFABackupCodeVerifySerializer,
)
from users.models import UserMFADevice
from households.models import Household

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserSerializer:
    """Test UserSerializer."""

    def test_serialize_user_all_fields(self):
        """Test serializing user with all fields."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
            phone_number="+1234567890",
            email_verified=True,
            locale="en-us",
            role="parent",
            household=household,
        )

        serializer = UserSerializer(user)
        data = serializer.data

        assert data["email"] == "test@example.com"
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["full_name"] == "John Doe"
        assert data["phone_number"] == "+1234567890"
        assert data["email_verified"] is True
        assert data["locale"] == "en-us"
        assert data["role"] == "parent"
        assert data["household"] == household.id
        assert data["is_active"] is True
        assert data["has_mfa_enabled"] is False
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_full_name_method(self):
        """Test get_full_name serializer method."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="Jane",
            last_name="Smith",
        )

        serializer = UserSerializer(user)
        assert serializer.data["full_name"] == "Jane Smith"

    def test_get_full_name_fallback_to_email(self):
        """Test full_name falls back to email when no name."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        serializer = UserSerializer(user)
        assert serializer.data["full_name"] == "test@example.com"

    def test_has_mfa_enabled_true(self):
        """Test has_mfa_enabled returns True when MFA is enabled."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        UserMFADevice.objects.create(user=user, secret_key="SECRET123", is_enabled=True)

        serializer = UserSerializer(user)
        assert serializer.data["has_mfa_enabled"] is True

    def test_has_mfa_enabled_false_when_not_enabled(self):
        """Test has_mfa_enabled returns False when MFA not enabled."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        UserMFADevice.objects.create(
            user=user, secret_key="SECRET123", is_enabled=False
        )

        serializer = UserSerializer(user)
        assert serializer.data["has_mfa_enabled"] is False

    def test_has_mfa_enabled_false_when_no_device(self):
        """Test has_mfa_enabled returns False when no MFA device exists."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        serializer = UserSerializer(user)
        assert serializer.data["has_mfa_enabled"] is False

    def test_read_only_fields(self):
        """Test read-only fields cannot be updated."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        serializer = UserSerializer(
            user,
            data={
                "email": "newemail@example.com",
                "email_verified": True,
                "role": "admin",
                "is_active": False,
                "first_name": "Updated",
            },
            partial=True,
        )

        assert serializer.is_valid()
        updated_user = serializer.save()

        # Read-only fields should not change
        assert updated_user.email == "test@example.com"
        assert updated_user.email_verified is False
        assert updated_user.role == "observer"
        assert updated_user.is_active is True

        # Writable field should update
        assert updated_user.first_name == "Updated"


@pytest.mark.django_db
@pytest.mark.unit
class TestMFATokenObtainPairSerializer:
    """Test MFATokenObtainPairSerializer."""

    @pytest.mark.skip(reason="Axes integration requires full request context")
    @patch("users.serializers_auth.verify_totp_code")
    def test_validate_with_mfa_enabled_valid_otp(self, mock_verify_totp):
        """Test validation succeeds with valid OTP when MFA is enabled."""
        mock_verify_totp.return_value = True

        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        UserMFADevice.objects.create(user=user, secret_key="SECRET123", is_enabled=True)

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "test@example.com",
                "password": "testpass123",
                "otp": "123456",
            }
        )

        assert serializer.is_valid()
        mock_verify_totp.assert_called_once_with(user, "123456")

    @pytest.mark.skip(reason="Axes integration requires full request context")
    @patch("users.serializers_auth.verify_backup_code")
    def test_validate_with_mfa_enabled_valid_backup_code(self, mock_verify_backup):
        """Test validation succeeds with valid backup code when MFA is enabled."""
        mock_verify_backup.return_value = True

        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        UserMFADevice.objects.create(user=user, secret_key="SECRET123", is_enabled=True)

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "test@example.com",
                "password": "testpass123",
                "backup_code": "backup-code-123",
            }
        )

        assert serializer.is_valid()
        mock_verify_backup.assert_called_once()

    @pytest.mark.skip(reason="Axes integration requires full request context")
    @patch("users.serializers_auth.verify_totp_code")
    def test_validate_with_mfa_enabled_invalid_otp(self, mock_verify_totp):
        """Test validation fails with invalid OTP when MFA is enabled."""
        mock_verify_totp.return_value = False

        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        UserMFADevice.objects.create(user=user, secret_key="SECRET123", is_enabled=True)

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "test@example.com",
                "password": "testpass123",
                "otp": "wrong",
            }
        )

        assert not serializer.is_valid()
        assert "Invalid MFA credentials" in str(serializer.errors)

    @pytest.mark.skip(reason="Axes integration requires full request context")
    def test_validate_with_mfa_enabled_no_code_provided(self):
        """Test validation fails when MFA enabled but no code provided."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        UserMFADevice.objects.create(user=user, secret_key="SECRET123", is_enabled=True)

        serializer = MFATokenObtainPairSerializer(
            data={"email": "test@example.com", "password": "testpass123"}
        )

        assert not serializer.is_valid()
        assert "MFA code required" in str(serializer.errors)

    @pytest.mark.skip(reason="Axes integration requires full request context")
    def test_validate_without_mfa(self):
        """Test validation succeeds without MFA when not enabled."""
        User.objects.create_user(email="test@example.com", password="testpass123")

        serializer = MFATokenObtainPairSerializer(
            data={"email": "test@example.com", "password": "testpass123"}
        )

        assert serializer.is_valid()


@pytest.mark.django_db
@pytest.mark.unit
class TestMFABeginSetupSerializer:
    """Test MFABeginSetupSerializer."""

    def test_has_provisioning_uri_field(self):
        """Test serializer has provisioning_uri read-only field."""
        serializer = MFABeginSetupSerializer()
        assert "provisioning_uri" in serializer.fields
        assert serializer.fields["provisioning_uri"].read_only is True


@pytest.mark.django_db
@pytest.mark.unit
class TestMFAConfirmSetupSerializer:
    """Test MFAConfirmSetupSerializer."""

    @patch("users.serializers_mfa.verify_totp_code")
    @patch("users.serializers_mfa.enable_mfa")
    @patch("users.serializers_mfa.generate_backup_codes")
    def test_validate_with_valid_code(self, mock_generate, mock_enable, mock_verify):
        """Test validation succeeds with valid TOTP code."""
        mock_verify.return_value = True
        mock_generate.return_value = ["code1", "code2"]

        user = User.objects.create_user(email="test@example.com", password="pass123")

        factory = APIRequestFactory()
        request = factory.post("/fake-url/")
        request.user = user

        serializer = MFAConfirmSetupSerializer(
            data={"code": "123456"}, context={"request": request}
        )

        assert serializer.is_valid()
        mock_verify.assert_called_once_with(user, "123456")

    @patch("users.serializers_mfa.verify_totp_code")
    def test_validate_with_invalid_code(self, mock_verify):
        """Test validation fails with invalid TOTP code."""
        mock_verify.return_value = False

        user = User.objects.create_user(email="test@example.com", password="pass123")

        factory = APIRequestFactory()
        request = factory.post("/fake-url/")
        request.user = user

        serializer = MFAConfirmSetupSerializer(
            data={"code": "wrong"}, context={"request": request}
        )

        assert not serializer.is_valid()
        assert "Invalid TOTP code" in str(serializer.errors)

    @patch("users.serializers_mfa.verify_totp_code")
    @patch("users.serializers_mfa.enable_mfa")
    @patch("users.serializers_mfa.generate_backup_codes")
    def test_save_enables_mfa_and_returns_backup_codes(
        self, mock_generate, mock_enable, mock_verify
    ):
        """Test save() enables MFA and returns backup codes."""
        mock_verify.return_value = True
        mock_generate.return_value = ["code1", "code2", "code3"]

        user = User.objects.create_user(email="test@example.com", password="pass123")

        factory = APIRequestFactory()
        request = factory.post("/fake-url/")
        request.user = user

        serializer = MFAConfirmSetupSerializer(
            data={"code": "123456"}, context={"request": request}
        )

        assert serializer.is_valid()
        result = serializer.save()

        mock_enable.assert_called_once_with(user)
        mock_generate.assert_called_once_with(user)
        assert result["backup_codes"] == ["code1", "code2", "code3"]


@pytest.mark.django_db
@pytest.mark.unit
class TestMFABackupCodeVerifySerializer:
    """Test MFABackupCodeVerifySerializer."""

    @patch("users.serializers_mfa.verify_backup_code")
    def test_validate_with_valid_backup_code(self, mock_verify):
        """Test validation succeeds with valid backup code."""
        mock_verify.return_value = True

        user = User.objects.create_user(email="test@example.com", password="pass123")

        factory = APIRequestFactory()
        request = factory.post("/fake-url/")
        request.user = user

        serializer = MFABackupCodeVerifySerializer(
            data={"code": "valid-backup-code"}, context={"request": request}
        )

        assert serializer.is_valid()
        mock_verify.assert_called_once_with(user, "valid-backup-code")

    @patch("users.serializers_mfa.verify_backup_code")
    def test_validate_with_invalid_backup_code(self, mock_verify):
        """Test validation fails with invalid backup code."""
        mock_verify.return_value = False

        user = User.objects.create_user(email="test@example.com", password="pass123")

        factory = APIRequestFactory()
        request = factory.post("/fake-url/")
        request.user = user

        serializer = MFABackupCodeVerifySerializer(
            data={"code": "invalid-code"}, context={"request": request}
        )

        assert not serializer.is_valid()
        assert "Invalid backup code" in str(serializer.errors)
