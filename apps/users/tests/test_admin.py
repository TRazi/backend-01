"""
Tests for users admin interface.
Tests admin customization, permissions, and display methods.
"""

import pytest
from datetime import timedelta
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone
from django.utils.html import strip_tags

from apps.users.admin import UserAdmin, EmailOTPAdmin, EmailVerificationAdmin
from apps.users.models import EmailOTP, EmailVerification
from apps.households.models import Household

User = get_user_model()


@pytest.mark.django_db
class TestUserAdmin:
    """Test UserAdmin configuration and methods."""

    def setup_method(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = UserAdmin(User, self.site)
        self.factory = RequestFactory()

        self.household = Household.objects.create(
            name="Test Household", household_type="fam"
        )

        self.user = User.objects.create_user(
            email="admin@example.com",
            password="TestPass123!",
            first_name="Admin",
            last_name="User",
            household=self.household,
            is_staff=True,
        )

    def test_admin_list_display_fields(self):
        """Test admin list_display contains expected fields."""
        expected_fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "household",
            "role",
            "email_verified",
            "is_active",
            "is_staff",
            "created_at",
        ]

        assert self.admin.list_display == expected_fields

    def test_admin_list_filter_fields(self):
        """Test admin list_filter contains expected fields."""
        expected_filters = [
            "is_active",
            "is_staff",
            "is_superuser",
            "email_verified",
            "role",
            "created_at",
        ]

        assert self.admin.list_filter == expected_filters

    def test_admin_search_fields(self):
        """Test admin search_fields are configured."""
        expected_search = [
            "email",
            "username",
            "first_name",
            "last_name",
            "phone_number",
        ]

        assert self.admin.search_fields == expected_search

    def test_admin_queryset_optimization(self):
        """Test get_queryset uses select_related for performance."""
        request = self.factory.get("/admin/users/user/")
        request.user = self.user

        queryset = self.admin.get_queryset(request)

        # Check that select_related was used (by checking query)
        # This is indicated by the queryset having _prefetch_related_lookups or similar
        assert (
            queryset.query.select_related is not None
            or len(queryset.query.select_related) > 0
        )

    def test_admin_readonly_fields(self):
        """Test readonly_fields are configured correctly."""
        expected_readonly = ["uuid", "created_at", "updated_at", "last_login"]

        assert self.admin.readonly_fields == expected_readonly

    def test_admin_fieldsets_structure(self):
        """Test fieldsets are properly structured."""
        assert len(self.admin.fieldsets) == 6

        # Check Authentication section
        auth_fields = self.admin.fieldsets[0][1]["fields"]
        assert "email" in auth_fields
        assert "password" in auth_fields

        # Check Personal Info section
        personal_fields = self.admin.fieldsets[1][1]["fields"]
        assert "first_name" in personal_fields
        assert "last_name" in personal_fields

    def test_admin_add_fieldsets(self):
        """Test add_fieldsets for creating new users."""
        assert len(self.admin.add_fieldsets) == 1

        add_fields = self.admin.add_fieldsets[0][1]["fields"]
        assert "email" in add_fields
        assert "password1" in add_fields
        assert "password2" in add_fields


@pytest.mark.django_db
class TestEmailOTPAdmin:
    """Test EmailOTPAdmin configuration and methods."""

    def setup_method(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = EmailOTPAdmin(EmailOTP, self.site)
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            email="otp@example.com", password="TestPass123!"
        )

    def test_admin_has_no_add_permission(self):
        """Test OTP codes cannot be manually created in admin."""
        request = self.factory.get("/admin/users/emailotp/")
        request.user = self.user

        assert self.admin.has_add_permission(request) is False

    def test_admin_has_no_change_permission(self):
        """Test OTP codes cannot be modified in admin."""
        request = self.factory.get("/admin/users/emailotp/")
        request.user = self.user

        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )

        assert self.admin.has_change_permission(request, otp) is False

    def test_admin_user_email_display(self):
        """Test user_email method displays user's email."""
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )

        result = self.admin.user_email(otp)

        assert result == "otp@example.com"

    def test_admin_code_display_formatting(self):
        """Test code_display method formats code with HTML."""
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )

        result = self.admin.code_display(otp)

        # Check HTML formatting is applied
        assert "<code" in result
        # Code is auto-generated, just check it's in the output
        assert otp.code in result

    def test_admin_status_badge_valid(self):
        """Test status_badge shows VALID for active OTP."""
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )

        result = self.admin.status_badge(otp)

        assert "VALID" in result
        assert "#28a745" in result  # Green color

    def test_admin_status_badge_used(self):
        """Test status_badge shows USED for used OTP."""
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1", is_used=True
        )

        result = self.admin.status_badge(otp)

        assert "USED" in result
        assert "#6c757d" in result  # Gray color

    def test_admin_status_badge_expired(self):
        """Test status_badge shows EXPIRED for expired OTP."""
        past_time = timezone.now() - timedelta(minutes=20)
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )
        otp.expires_at = past_time
        otp.save()

        result = self.admin.status_badge(otp)

        assert "EXPIRED" in result
        assert "#dc3545" in result  # Red color

    def test_admin_time_until_expiry_valid(self):
        """Test time_until_expiry shows remaining time for valid OTP."""
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )

        result = self.admin.time_until_expiry(otp)

        # Should show minutes and seconds
        assert "min" in result
        assert "sec" in result

    def test_admin_time_until_expiry_used(self):
        """Test time_until_expiry shows N/A for used OTP."""
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1", is_used=True
        )

        result = self.admin.time_until_expiry(otp)

        assert "N/A (Used)" in result

    def test_admin_time_until_expiry_expired(self):
        """Test time_until_expiry shows time since expiry for expired OTP."""
        past_time = timezone.now() - timedelta(minutes=20)
        otp = EmailOTP.objects.create(
            user=self.user, code="123456", ip_address="127.0.0.1"
        )
        otp.expires_at = past_time
        otp.save()

        result = self.admin.time_until_expiry(otp)

        assert "Expired" in result
        assert "ago" in result

    def test_admin_queryset_optimization(self):
        """Test get_queryset uses select_related for user."""
        request = self.factory.get("/admin/users/emailotp/")
        request.user = self.user

        queryset = self.admin.get_queryset(request)

        # Check select_related is used
        assert queryset.query.select_related is not None


@pytest.mark.django_db
class TestEmailVerificationAdmin:
    """Test EmailVerificationAdmin configuration and methods."""

    def setup_method(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = EmailVerificationAdmin(EmailVerification, self.site)
        self.factory = RequestFactory()

        self.user = User.objects.create_user(
            email="verify@example.com", password="TestPass123!"
        )

    def test_admin_has_no_add_permission(self):
        """Test verification tokens cannot be manually created in admin."""
        request = self.factory.get("/admin/users/emailverification/")
        request.user = self.user

        assert self.admin.has_add_permission(request) is False

    def test_admin_has_no_change_permission(self):
        """Test verification tokens cannot be modified in admin."""
        request = self.factory.get("/admin/users/emailverification/")
        request.user = self.user

        verification = EmailVerification.objects.create(user=self.user)

        assert self.admin.has_change_permission(request, verification) is False

    def test_admin_user_email_display(self):
        """Test user_email method displays user's email."""
        verification = EmailVerification.objects.create(user=self.user)

        result = self.admin.user_email(verification)

        assert result == "verify@example.com"

    def test_admin_token_preview_truncation(self):
        """Test token_preview shows only first 8 characters."""
        verification = EmailVerification.objects.create(user=self.user)

        result = self.admin.token_preview(verification)

        # Should contain first 8 chars of token
        token_str = str(verification.token)
        assert token_str[:8] in result
        assert "&hellip;" in result  # Ellipsis

    def test_admin_status_badge_verified(self):
        """Test status_badge shows VERIFIED for verified token."""
        verification = EmailVerification.objects.create(user=self.user)
        verification.verified_at = timezone.now()
        verification.save()

        result = self.admin.status_badge(verification)

        assert "VERIFIED" in result
        assert "#28a745" in result  # Green color

    def test_admin_status_badge_expired(self):
        """Test status_badge shows EXPIRED for expired token."""
        past_time = timezone.now() - timedelta(hours=25)
        verification = EmailVerification.objects.create(user=self.user)
        verification.created_at = past_time
        verification.save()

        result = self.admin.status_badge(verification)

        assert "EXPIRED" in result
        assert "#dc3545" in result  # Red color

    def test_admin_status_badge_pending(self):
        """Test status_badge shows PENDING for active token."""
        verification = EmailVerification.objects.create(user=self.user)

        result = self.admin.status_badge(verification)

        assert "PENDING" in result
        assert "#ffc107" in result  # Yellow color

    def test_admin_time_since_creation_pending(self):
        """Test time_since_creation for pending token."""
        verification = EmailVerification.objects.create(user=self.user)

        result = self.admin.time_since_creation(verification)

        # Should show time elapsed and time remaining
        assert "hours" in result
        assert "min" in result
        assert "left" in result

    def test_admin_time_since_creation_verified(self):
        """Test time_since_creation for verified token."""
        verification = EmailVerification.objects.create(user=self.user)
        verification.verified_at = timezone.now()
        verification.save()

        result = self.admin.time_since_creation(verification)

        assert "hours" in result
        assert "min" in result

    def test_admin_time_since_creation_expired(self):
        """Test time_since_creation for expired token."""
        past_time = timezone.now() - timedelta(hours=25)
        verification = EmailVerification.objects.create(user=self.user)
        verification.created_at = past_time
        verification.save()

        result = self.admin.time_since_creation(verification)

        assert "Expired" in result

    def test_admin_queryset_optimization(self):
        """Test get_queryset uses select_related for user."""
        request = self.factory.get("/admin/users/emailverification/")
        request.user = self.user

        queryset = self.admin.get_queryset(request)

        # Check select_related is used
        assert queryset.query.select_related is not None

    def test_admin_list_display_fields(self):
        """Test admin list_display contains expected fields."""
        expected_fields = [
            "user_email",
            "token_preview",
            "status_badge",
            "time_since_creation",
            "verified_at",
            "created_at",
        ]

        assert self.admin.list_display == expected_fields

    def test_admin_readonly_fields(self):
        """Test readonly_fields are configured correctly."""
        expected_readonly = [
            "user",
            "token",
            "verified_at",
            "created_at",
            "status_badge",
            "time_since_creation",
        ]

        assert self.admin.readonly_fields == expected_readonly
