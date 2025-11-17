"""
Tests for User and UserMFADevice models.
Tests model validation, email normalization, methods, and properties.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from apps.users.models import User, UserMFADevice
from apps.households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
class TestUserModel:
    """Test User model functionality."""

    def test_create_user_basic(self):
        """Test creating a user with basic fields."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
        )

        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.is_active is True
        assert user.is_staff is False
        assert user.check_password("testpass123")

    def test_email_normalization_on_save(self):
        """Test that email is normalized to lowercase on save."""
        user = User.objects.create_user(
            email="Test@Example.COM", password="testpass123"
        )

        assert user.email == "test@example.com"

    def test_email_normalization_on_clean(self):
        """Test that clean() normalizes email."""
        user = User(email="Another@TEST.com")
        user.clean()

        assert user.email == "another@test.com"

    def test_email_unique_constraint(self):
        """Test that duplicate emails are not allowed."""
        User.objects.create_user(email="test@example.com", password="pass123")

        with pytest.raises(IntegrityError):
            User.objects.create_user(email="test@example.com", password="pass456")

    def test_email_case_insensitive_unique(self):
        """Test that email uniqueness is case-insensitive."""
        User.objects.create_user(email="test@example.com", password="pass123")

        with pytest.raises(IntegrityError):
            User.objects.create_user(email="TEST@EXAMPLE.COM", password="pass456")

    def test_user_str_representation(self):
        """Test __str__ method returns email."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert str(user) == "test@example.com"

    def test_get_full_name_with_both_names(self):
        """Test get_full_name returns first and last name."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
        )

        assert user.get_full_name() == "John Doe"

    def test_get_full_name_with_first_only(self):
        """Test get_full_name with only first name."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", first_name="John"
        )

        assert user.get_full_name() == "John"

    def test_get_full_name_with_last_only(self):
        """Test get_full_name with only last name."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", last_name="Doe"
        )

        assert user.get_full_name() == "Doe"

    def test_get_full_name_fallback_to_email(self):
        """Test get_full_name returns email when no name."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.get_full_name() == "test@example.com"

    def test_get_short_name_returns_first_name(self):
        """Test get_short_name returns first name."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", first_name="John"
        )

        assert user.get_short_name() == "John"

    def test_get_short_name_fallback_to_email(self):
        """Test get_short_name returns email when no first name."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.get_short_name() == "test@example.com"

    def test_phone_number_valid_format(self):
        """Test phone number accepts valid international format."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", phone_number="+1234567890"
        )

        user.full_clean()  # Should not raise
        assert user.phone_number == "+1234567890"

    def test_phone_number_invalid_format(self):
        """Test phone number rejects invalid format."""
        user = User(email="test@example.com", phone_number="invalid-phone")

        with pytest.raises(ValidationError) as exc_info:
            user.full_clean()

        assert "phone_number" in exc_info.value.error_dict

    def test_phone_number_optional(self):
        """Test phone number is optional."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        user.full_clean()  # Should not raise
        assert user.phone_number == ""

    def test_default_locale(self):
        """Test default locale is en-nz."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.locale == "en-nz"

    def test_default_role(self):
        """Test default role is observer."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.role == "observer"

    def test_user_with_household(self):
        """Test user can be associated with household."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@example.com", password="pass123", household=household
        )

        assert user.household == household

    def test_user_household_set_null_on_delete(self):
        """Test household is set to NULL when deleted."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@example.com", password="pass123", household=household
        )

        household.delete()
        user.refresh_from_db()

        assert user.household is None

    def test_email_verified_default_false(self):
        """Test email_verified defaults to False."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.email_verified is False

    def test_is_active_default_true(self):
        """Test is_active defaults to True."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.is_active is True

    def test_is_staff_default_false(self):
        """Test is_staff defaults to False."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        assert user.is_staff is False


@pytest.mark.django_db
@pytest.mark.unit
class TestUserMFADeviceModel:
    """Test UserMFADevice model functionality."""

    def test_create_mfa_device(self):
        """Test creating an MFA device for a user."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(
            user=user, secret_key="TESTSECRETKEY123", is_enabled=False
        )

        assert device.user == user
        assert device.secret_key == "TESTSECRETKEY123"
        assert device.is_enabled is False
        assert device.backup_codes == []
        assert device.last_used_at is None

    def test_mfa_device_one_to_one_relationship(self):
        """Test MFA device has one-to-one relationship with user."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(user=user, secret_key="SECRET123")

        # Access from user side
        assert user.mfa_device == device

    def test_mfa_device_str_representation(self):
        """Test __str__ method."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(user=user, secret_key="SECRET123")

        assert str(device) == "MFA device for test@example.com"

    def test_mfa_device_deleted_with_user(self):
        """Test MFA device is deleted when user is deleted."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(user=user, secret_key="SECRET123")

        device_id = device.id
        user.delete()

        assert not UserMFADevice.objects.filter(id=device_id).exists()

    def test_mfa_device_default_is_enabled_false(self):
        """Test is_enabled defaults to False."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(user=user, secret_key="SECRET123")

        assert device.is_enabled is False

    def test_mfa_device_backup_codes_default_empty(self):
        """Test backup_codes defaults to empty list."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(user=user, secret_key="SECRET123")

        assert device.backup_codes == []

    def test_mfa_device_backup_codes_json_field(self):
        """Test backup_codes can store JSON list."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        codes = ["code1", "code2", "code3"]
        device = UserMFADevice.objects.create(
            user=user, secret_key="SECRET123", backup_codes=codes
        )

        device.refresh_from_db()
        assert device.backup_codes == codes

    def test_mfa_device_last_used_at_optional(self):
        """Test last_used_at is optional."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        device = UserMFADevice.objects.create(user=user, secret_key="SECRET123")

        assert device.last_used_at is None
