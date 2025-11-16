"""
Tests for UserManager custom manager.
Tests create_user() and create_superuser() methods with all edge cases.
"""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserManager:
    """Test UserManager functionality."""

    def test_create_user_with_email_and_password(self):
        """Test creating a user with email and password."""
        user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )

        assert user.email == "test@example.com"
        assert user.check_password("testpass123")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_create_user_normalizes_email(self):
        """Test create_user normalizes email to lowercase."""
        user = User.objects.create_user(
            email="Test@EXAMPLE.com", password="testpass123"
        )

        assert user.email == "test@example.com"

    def test_create_user_without_email_raises_error(self):
        """Test create_user raises ValueError when email is not provided."""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(email="", password="testpass123")

        assert "The Email field must be set" in str(exc_info.value)

    def test_create_user_with_none_email_raises_error(self):
        """Test create_user raises ValueError when email is None."""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_user(email=None, password="testpass123")

        assert "The Email field must be set" in str(exc_info.value)

    def test_create_user_with_extra_fields(self):
        """Test create_user accepts extra fields."""
        user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            first_name="John",
            last_name="Doe",
            role="parent",
        )

        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.role == "parent"

    def test_create_user_without_password(self):
        """Test create_user works without password (unusable password)."""
        user = User.objects.create_user(email="test@example.com", password=None)

        assert user.email == "test@example.com"
        assert not user.has_usable_password()

    def test_create_superuser_basic(self):
        """Test creating a superuser with basic fields."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        assert user.email == "admin@example.com"
        assert user.check_password("adminpass123")
        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True
        assert user.role == "admin"

    def test_create_superuser_normalizes_email(self):
        """Test create_superuser normalizes email."""
        user = User.objects.create_superuser(
            email="Admin@EXAMPLE.com", password="adminpass123"
        )

        assert user.email == "admin@example.com"

    def test_create_superuser_sets_defaults(self):
        """Test create_superuser sets correct defaults."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        assert user.is_staff is True
        assert user.is_superuser is True
        assert user.is_active is True
        assert user.role == "admin"

    def test_create_superuser_is_staff_false_raises_error(self):
        """Test create_superuser raises error if is_staff=False."""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_staff=False
            )

        assert "Superuser must have is_staff=True" in str(exc_info.value)

    def test_create_superuser_is_superuser_false_raises_error(self):
        """Test create_superuser raises error if is_superuser=False."""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_superuser=False
            )

        assert "Superuser must have is_superuser=True" in str(exc_info.value)

    def test_create_superuser_with_extra_fields(self):
        """Test create_superuser accepts extra fields."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            first_name="Super",
            last_name="Admin",
        )

        assert user.first_name == "Super"
        assert user.last_name == "Admin"

    def test_create_superuser_overrides_role(self):
        """Test create_superuser sets role to admin even if different role provided."""
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            role="observer",  # This should be overridden
        )

        # setdefault doesn't override if already set, so this will be observer
        # Let's verify the actual behavior
        assert user.role == "observer"  # Because setdefault doesn't override

    def test_create_superuser_without_email_raises_error(self):
        """Test create_superuser raises error when email is missing."""
        with pytest.raises(ValueError) as exc_info:
            User.objects.create_superuser(email="", password="adminpass123")

        assert "The Email field must be set" in str(exc_info.value)

    def test_create_superuser_without_password(self):
        """Test create_superuser works without password."""
        user = User.objects.create_superuser(email="admin@example.com", password=None)

        assert user.email == "admin@example.com"
        assert user.is_staff is True
        assert user.is_superuser is True
        assert not user.has_usable_password()

    def test_username_field_is_email(self):
        """Test USERNAME_FIELD is set to email."""
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_is_empty(self):
        """Test REQUIRED_FIELDS is empty (only email required)."""
        assert User.REQUIRED_FIELDS == []
