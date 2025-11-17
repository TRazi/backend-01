"""
Tests for MFA authentication serializers.
Tests MFATokenObtainPairSerializer with TOTP and backup code validation.
"""

import pytest
import pyotp
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.test import RequestFactory
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from apps.users.serializers_auth import MFATokenObtainPairSerializer
from apps.users.models import UserMFADevice
from apps.users.services.mfa import generate_backup_codes

User = get_user_model()


@pytest.mark.django_db
class TestMFATokenObtainPairSerializer:
    """Test MFA-enabled JWT token generation."""

    def setup_method(self):
        """Set up test users and request factory."""
        self.factory = RequestFactory()

        self.user_no_mfa = User.objects.create_user(
            email="nomfa@example.com", password="TestPass123!"
        )

        self.user_with_mfa = User.objects.create_user(
            email="mfa@example.com", password="TestPass123!"
        )

        # Enable MFA for second user
        self.secret = pyotp.random_base32()
        self.device = UserMFADevice.objects.create(
            user=self.user_with_mfa, is_enabled=True, secret_key=self.secret
        )

    def test_validate_without_mfa_succeeds(self):
        """User without MFA should get token normally."""
        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={"email": "nomfa@example.com", "password": "TestPass123!"},
            context={"request": request},
        )

        assert serializer.is_valid()
        tokens = serializer.validated_data
        assert "access" in tokens
        assert "refresh" in tokens

    def test_mfa_enabled_requires_code(self):
        """User with MFA must provide OTP or backup code."""
        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                # Missing OTP/backup code
            },
            context={"request": request},
        )

        with pytest.raises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)

        assert "mfa_required" in str(exc.value) or "MFA code required" in str(exc.value)

    def test_mfa_enabled_valid_otp_succeeds(self):
        """Valid TOTP code should grant access."""
        # Generate valid OTP
        totp = pyotp.TOTP(self.secret)
        valid_otp = totp.now()

        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                "otp": valid_otp,
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        tokens = serializer.validated_data
        assert "access" in tokens
        assert "refresh" in tokens

    def test_mfa_enabled_invalid_otp_fails(self):
        """Invalid TOTP code should be rejected."""
        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                "otp": "000000",  # Invalid OTP
            },
            context={"request": request},
        )

        with pytest.raises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)

        assert "invalid_mfa" in str(exc.value) or "Invalid MFA credentials" in str(exc.value)

    def test_mfa_enabled_valid_backup_code_succeeds(self):
        """Valid backup code should grant access."""
        # Generate and store backup code
        backup_code = "4-'jc*oSJ@axCjx!"
        hashed = make_password(backup_code)

        self.device.backup_codes = [hashed]
        self.device.save()

        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                "backup_code": backup_code,
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        tokens = serializer.validated_data
        assert "access" in tokens
        assert "refresh" in tokens

    def test_mfa_enabled_invalid_backup_code_fails(self):
        """Invalid backup code should be rejected."""
        # Store a different backup code
        real_code = "4-'jc*oSJ@axCjx!"
        hashed = make_password(real_code)

        self.device.backup_codes = [hashed]
        self.device.save()

        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                "backup_code": "99999999",  # Wrong code
            },
            context={"request": request},
        )

        with pytest.raises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)

        assert "invalid_mfa" in str(exc.value) or "Invalid MFA credentials" in str(exc.value)

    def test_mfa_enabled_both_otp_and_backup_code_otp_wins(self):
        """If both OTP and backup code provided, OTP takes precedence."""
        # Generate valid OTP
        totp = pyotp.TOTP(self.secret)
        valid_otp = totp.now()

        request = self.factory.post("/api/auth/token/")

        # Also provide a backup code (will be ignored)
        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                "otp": valid_otp,
                "backup_code": "ignored",
            },
            context={"request": request},
        )

        # Should succeed because OTP is valid
        assert serializer.is_valid()

    def test_mfa_disabled_device_exists_but_not_enabled(self):
        """Disabled MFA device should not require code."""
        # Create user with disabled MFA device
        user_disabled_mfa = User.objects.create_user(
            email="disabled@example.com", password="TestPass123!"
        )

        UserMFADevice.objects.create(
            user=user_disabled_mfa,
            is_enabled=False,  # Disabled
            secret_key=pyotp.random_base32(),
        )

        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "disabled@example.com",
                "password": "TestPass123!",
                # No OTP code needed
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        tokens = serializer.validated_data
        assert "access" in tokens

    def test_wrong_password_fails_before_mfa_check(self):
        """Wrong password should fail before MFA validation."""
        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "WrongPassword123!",
                "otp": "123456",
            },
            context={"request": request},
        )

        with pytest.raises(AuthenticationFailed):
            serializer.is_valid(raise_exception=True)

    def test_blank_otp_and_backup_code_fails(self):
        """Empty strings for OTP/backup code should fail."""
        request = self.factory.post("/api/auth/token/")

        serializer = MFATokenObtainPairSerializer(
            data={
                "email": "mfa@example.com",
                "password": "TestPass123!",
                "otp": "",
                "backup_code": "",
            },
            context={"request": request},
        )

        with pytest.raises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)

        assert "mfa_required" in str(exc.value) or "MFA code required" in str(exc.value)
