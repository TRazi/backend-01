"""
Tests for MFA services.
Tests all MFA service functions including TOTP and backup codes.
"""

import pytest
from unittest.mock import patch, MagicMock
import pyotp
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.users.services.mfa import (
    get_or_create_mfa_device,
    generate_provisioning_uri,
    verify_totp_code,
    generate_backup_codes,
    verify_backup_code,
    enable_mfa,
    disable_mfa,
    _generate_backup_code,
)
from apps.users.models import UserMFADevice

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestMFAServices:
    """Test MFA service functions."""

    def test_get_or_create_mfa_device_creates_new(self):
        """Test get_or_create_mfa_device creates new device."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = get_or_create_mfa_device(user)

        assert device.user == user
        assert device.secret_key  # Should have a secret key
        assert device.is_enabled is False
        assert device.backup_codes == []

    def test_get_or_create_mfa_device_returns_existing(self):
        """Test get_or_create_mfa_device returns existing device."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Create device
        device1 = get_or_create_mfa_device(user)
        original_secret = device1.secret_key

        # Get same device
        device2 = get_or_create_mfa_device(user)

        assert device1.id == device2.id
        assert device2.secret_key == original_secret

    def test_generate_provisioning_uri(self):
        """Test generate_provisioning_uri creates valid TOTP URI."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        uri = generate_provisioning_uri(user)

        assert uri.startswith("otpauth://totp/")
        # Email is URL-encoded in the URI
        assert "test@example.com" in uri or "test%40example.com" in uri
        assert "KinWise" in uri  # Default issuer
        assert "secret=" in uri

    def test_verify_totp_code_with_valid_code(self):
        """Test verify_totp_code returns True for valid code."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(
            user=user, secret_key=pyotp.random_base32(), is_enabled=True
        )

        # Generate valid code
        totp = pyotp.TOTP(device.secret_key)
        valid_code = totp.now()

        result = verify_totp_code(user, valid_code)

        assert result is True

        # Check last_used_at was updated
        device.refresh_from_db()
        assert device.last_used_at is not None

    def test_verify_totp_code_with_invalid_code(self):
        """Test verify_totp_code returns False for invalid code."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        UserMFADevice.objects.create(
            user=user, secret_key=pyotp.random_base32(), is_enabled=True
        )

        result = verify_totp_code(user, "000000")  # Invalid code

        assert result is False

    def test_verify_totp_code_no_device(self):
        """Test verify_totp_code returns False when no MFA device."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        result = verify_totp_code(user, "123456")

        assert result is False

    def test_verify_totp_code_updates_last_used_at(self):
        """Test verify_totp_code updates last_used_at on success."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(
            user=user, secret_key=pyotp.random_base32(), is_enabled=True
        )

        totp = pyotp.TOTP(device.secret_key)
        valid_code = totp.now()

        before_time = timezone.now()
        verify_totp_code(user, valid_code)

        device.refresh_from_db()
        assert device.last_used_at is not None
        assert device.last_used_at >= before_time

    def test_generate_backup_codes_default_count(self):
        """Test generate_backup_codes generates 10 codes by default."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        codes = generate_backup_codes(user)

        assert len(codes) == 10
        assert all(isinstance(code, str) for code in codes)

    def test_generate_backup_codes_custom_count(self):
        """Test generate_backup_codes generates custom count."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        codes = generate_backup_codes(user, count=5)

        assert len(codes) == 5

    def test_generate_backup_codes_stores_hashed(self):
        """Test generate_backup_codes stores hashed versions."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        raw_codes = generate_backup_codes(user)

        device = user.mfa_device
        assert len(device.backup_codes) == len(raw_codes)

        # Codes should be hashed (not equal to raw)
        assert all(hashed != raw for hashed, raw in zip(device.backup_codes, raw_codes))

    def test_verify_backup_code_with_valid_code(self):
        """Test verify_backup_code returns True and consumes code."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        raw_codes = generate_backup_codes(user, count=3)

        device = user.mfa_device
        initial_count = len(device.backup_codes)

        # Use first code
        result = verify_backup_code(user, raw_codes[0])

        assert result is True

        # Code should be consumed
        device.refresh_from_db()
        assert len(device.backup_codes) == initial_count - 1
        assert device.last_used_at is not None

    def test_verify_backup_code_with_invalid_code(self):
        """Test verify_backup_code returns False for invalid code."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        generate_backup_codes(user)

        result = verify_backup_code(user, "invalid-code")

        assert result is False

    def test_verify_backup_code_no_device(self):
        """Test verify_backup_code returns False when no MFA device."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        result = verify_backup_code(user, "some-code")

        assert result is False

    def test_verify_backup_code_updates_last_used_at(self):
        """Test verify_backup_code updates last_used_at on success."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        raw_codes = generate_backup_codes(user)

        before_time = timezone.now()
        verify_backup_code(user, raw_codes[0])

        device = user.mfa_device
        device.refresh_from_db()
        assert device.last_used_at is not None
        assert device.last_used_at >= before_time

    def test_enable_mfa(self):
        """Test enable_mfa sets is_enabled to True."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = get_or_create_mfa_device(user)
        assert device.is_enabled is False

        enable_mfa(user)

        device.refresh_from_db()
        assert device.is_enabled is True

    def test_disable_mfa(self):
        """Test disable_mfa sets is_enabled to False and clears backup codes."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Enable MFA and generate backup codes
        device = get_or_create_mfa_device(user)
        device.is_enabled = True
        device.backup_codes = ["code1", "code2"]
        device.save()

        disable_mfa(user)

        device.refresh_from_db()
        assert device.is_enabled is False
        assert device.backup_codes == []

    def test_disable_mfa_no_device(self):
        """Test disable_mfa handles user without MFA device."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        # Should not raise error
        disable_mfa(user)

    def test_generate_backup_code_format(self):
        """Test _generate_backup_code returns URL-safe string."""
        code = _generate_backup_code()

        assert isinstance(code, str)
        assert len(code) > 0
        # URL-safe means no +, /, = characters that need encoding
        assert all(c.isalnum() or c in "-_" for c in code)

    def test_backup_codes_are_unique(self):
        """Test generated backup codes are unique."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        codes = generate_backup_codes(user, count=10)

        assert len(codes) == len(set(codes))  # All unique

    def test_verify_backup_code_consumed_only_once(self):
        """Test backup code can only be used once."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        raw_codes = generate_backup_codes(user, count=3)
        code_to_use = raw_codes[0]

        # First use should succeed
        result1 = verify_backup_code(user, code_to_use)
        assert result1 is True

        # Second use should fail
        result2 = verify_backup_code(user, code_to_use)
        assert result2 is False
