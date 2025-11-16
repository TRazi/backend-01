"""
Tests for audit admin interfaces.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from decimal import Decimal

from audit.admin import AuditLogAdmin, FailedLoginAttemptAdmin, DataExportLogAdmin
from audit.models import AuditLog, FailedLoginAttempt, DataExportLog
from households.models import Household

User = get_user_model()


@pytest.mark.django_db
class TestAuditLogAdmin:
    """Test AuditLogAdmin interface."""

    def test_list_display_fields(self):
        """Verify list_display contains expected fields."""
        admin = AuditLogAdmin(AuditLog, AdminSite())

        assert "created_at" in admin.list_display
        assert "user_email" in admin.list_display
        assert "action_type" in admin.list_display
        assert "success_badge" in admin.list_display

    def test_user_email_with_user(self):
        """Display user email when user exists."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@example.com", password="pass123", household=household
        )

        log = AuditLog.objects.create(
            user=user,
            action_type="read",
            action_description="Test action",
            success=True,
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.user_email(log) == "test@example.com"

    def test_user_email_without_user(self):
        """Display 'System' when no user."""
        log = AuditLog.objects.create(
            action_type="read", action_description="System action", success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.user_email(log) == "System"

    def test_action_description_short_truncates(self):
        """Long descriptions are truncated."""
        long_description = "A" * 100
        log = AuditLog.objects.create(
            action_type="read", action_description=long_description, success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        short = admin.action_description_short(log)

        assert len(short) <= 63  # 60 + "..."
        assert short.endswith("...")

    def test_action_description_short_no_truncate(self):
        """Short descriptions are not truncated."""
        short_description = "Short action"
        log = AuditLog.objects.create(
            action_type="read", action_description=short_description, success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        result = admin.action_description_short(log)

        assert result == short_description
        assert not result.endswith("...")

    def test_object_link_with_no_object(self):
        """Object link returns dash when no object."""
        log = AuditLog.objects.create(
            action_type="read", action_description="Test", success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.object_link(log) == "-"

    def test_household_link_with_household(self):
        """Household link displays household name."""
        household = Household.objects.create(name="Test Family")
        log = AuditLog.objects.create(
            action_type="read",
            action_description="Test",
            household=household,
            success=True,
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        result = admin.household_link(log)

        assert "Test Family" in result

    def test_household_link_without_household(self):
        """Household link returns dash when no household."""
        log = AuditLog.objects.create(
            action_type="read", action_description="Test", success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.household_link(log) == "-"

    def test_success_badge_true(self):
        """Success badge shows green checkmark for successful actions."""
        log = AuditLog.objects.create(
            action_type="read", action_description="Test", success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        badge = admin.success_badge(log)

        assert "green" in str(badge)
        assert "Success" in str(badge)

    def test_success_badge_false(self):
        """Success badge shows red X for failed actions."""
        log = AuditLog.objects.create(
            action_type="read", action_description="Test", success=False
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        badge = admin.success_badge(log)

        assert "red" in str(badge)
        assert "Failed" in str(badge)

    def test_changes_formatted_with_changes(self):
        """Changes are formatted as JSON."""
        log = AuditLog.objects.create(
            action_type="update",
            action_description="Test",
            changes={"field": "value"},
            success=True,
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        formatted = admin.changes_formatted(log)

        assert "<pre>" in str(formatted)
        assert "field" in str(formatted)

    def test_changes_formatted_no_changes(self):
        """Returns dash when no changes."""
        log = AuditLog.objects.create(
            action_type="read", action_description="Test", success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.changes_formatted(log) == "-"

    def test_metadata_formatted_with_metadata(self):
        """Metadata is formatted as JSON."""
        log = AuditLog.objects.create(
            action_type="read",
            action_description="Test",
            metadata={"key": "value"},
            success=True,
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        formatted = admin.metadata_formatted(log)

        assert "<pre>" in str(formatted)
        assert "key" in str(formatted)

    def test_metadata_formatted_no_metadata(self):
        """Returns dash when no metadata."""
        log = AuditLog.objects.create(
            action_type="read", action_description="Test", success=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.metadata_formatted(log) == "-"

    def test_has_add_permission_false(self):
        """Audit logs cannot be manually added."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.has_add_permission(request) is False

    def test_has_change_permission_false(self):
        """Audit logs cannot be modified."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.has_change_permission(request) is False

    def test_has_delete_permission_regular_user(self):
        """Regular staff cannot delete audit logs."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="staff@test.com",
            password="pass123",
            is_staff=True,
            is_superuser=False,
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.has_delete_permission(request) is False

    def test_has_delete_permission_superuser(self):
        """Superusers can delete audit logs."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="super@test.com", password="pass123", is_staff=True, is_superuser=True
        )

        admin = AuditLogAdmin(AuditLog, AdminSite())
        assert admin.has_delete_permission(request) is True


@pytest.mark.django_db
class TestFailedLoginAttemptAdmin:
    """Test FailedLoginAttemptAdmin interface."""

    def test_list_display_fields(self):
        """Verify list_display contains expected fields."""
        admin = FailedLoginAttemptAdmin(FailedLoginAttempt, AdminSite())

        assert "created_at" in admin.list_display
        assert "username" in admin.list_display
        assert "ip_address" in admin.list_display
        assert "attempt_count" in admin.list_display
        assert "locked_out_badge" in admin.list_display

    def test_locked_out_badge_true(self):
        """Locked out badge shows red for locked accounts."""
        attempt = FailedLoginAttempt.objects.create(
            username="test@test.com", ip_address="127.0.0.1", locked_out=True
        )

        admin = FailedLoginAttemptAdmin(FailedLoginAttempt, AdminSite())
        badge = admin.locked_out_badge(attempt)

        assert "red" in str(badge)
        assert "Locked" in str(badge)

    def test_locked_out_badge_false(self):
        """Locked out badge shows gray dash when not locked."""
        attempt = FailedLoginAttempt.objects.create(
            username="test@test.com", ip_address="127.0.0.1", locked_out=False
        )

        admin = FailedLoginAttemptAdmin(FailedLoginAttempt, AdminSite())
        badge = admin.locked_out_badge(attempt)

        assert "gray" in str(badge)
        assert "-" in str(badge)

    def test_resolved_badge_true(self):
        """Resolved badge shows green for resolved attempts."""
        user = User.objects.create_user(email="admin@test.com", password="pass123")

        attempt = FailedLoginAttempt.objects.create(
            username="test@test.com",
            ip_address="127.0.0.1",
            resolved=True,
            resolved_by=user,
        )

        admin = FailedLoginAttemptAdmin(FailedLoginAttempt, AdminSite())
        badge = admin.resolved_badge(attempt)

        assert "green" in str(badge)
        assert "Resolved" in str(badge)

    def test_resolved_badge_false(self):
        """Resolved badge shows warning when not resolved."""
        attempt = FailedLoginAttempt.objects.create(
            username="test@test.com", ip_address="127.0.0.1", resolved=False
        )

        admin = FailedLoginAttemptAdmin(FailedLoginAttempt, AdminSite())
        badge = admin.resolved_badge(attempt)

        assert "orange" in str(badge)
        assert "Pending" in str(badge)

    def test_has_add_permission_false(self):
        """Failed login attempts cannot be manually added."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = FailedLoginAttemptAdmin(FailedLoginAttempt, AdminSite())
        assert admin.has_add_permission(request) is False


@pytest.mark.django_db
class TestDataExportLogAdmin:
    """Test DataExportLogAdmin interface."""

    def test_list_display_fields(self):
        """Verify list_display contains expected fields."""
        admin = DataExportLogAdmin(DataExportLog, AdminSite())

        assert "created_at" in admin.list_display
        assert "user_email" in admin.list_display
        assert "export_type" in admin.list_display
        assert "file_size_display" in admin.list_display

    def test_user_email_with_user(self):
        """Display user email when user exists."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.user_email(export) == "test@test.com"

    def test_user_email_without_user(self):
        """Display Unknown when no user."""
        household = Household.objects.create(name="Test Family")

        export = DataExportLog.objects.create(
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.user_email(export) == "Unknown"

    def test_household_link_with_household(self):
        """Household link displays household name."""
        household = Household.objects.create(name="Export Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=50,
            ip_address="127.0.0.1",
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        result = admin.household_link(export)

        assert "Export Family" in result

    def test_household_link_without_household(self):
        """Household link returns dash when no household."""
        user = User.objects.create_user(email="test@test.com", password="pass123")

        export = DataExportLog.objects.create(
            user=user, export_type="user_data", record_count=10, ip_address="127.0.0.1"
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.household_link(export) == "-"

    def test_file_size_display_bytes(self):
        """File size display formats bytes correctly."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
            file_size_bytes=512,
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        size = admin.file_size_display(export)

        assert "512" in size
        assert "B" in size

    def test_file_size_display_kilobytes(self):
        """File size display formats kilobytes correctly."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
            file_size_bytes=2048,
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        size = admin.file_size_display(export)

        assert "2.0" in size
        assert "KB" in size

    def test_file_size_display_megabytes(self):
        """File size display formats megabytes correctly."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
            file_size_bytes=1048576,  # 1 MB
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        size = admin.file_size_display(export)

        assert "1.0" in size
        assert "MB" in size

    def test_file_size_display_no_size(self):
        """File size display returns dash when no size."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.file_size_display(export) == "-"

    def test_export_filters_formatted_with_filters(self):
        """Export filters are formatted as JSON."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
            export_filters={"category": "food", "amount_min": 50},
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        formatted = admin.export_filters_formatted(export)

        assert "<pre>" in str(formatted)
        assert "category" in str(formatted)

    def test_export_filters_formatted_no_filters(self):
        """Returns dash when no filters."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="test@test.com", password="pass123", household=household
        )

        export = DataExportLog.objects.create(
            user=user,
            household=household,
            export_type="household_data",
            record_count=100,
            ip_address="127.0.0.1",
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.export_filters_formatted(export) == "-"

    def test_has_add_permission_false(self):
        """Data export logs cannot be manually added."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.has_add_permission(request) is False

    def test_has_change_permission_false(self):
        """Data export logs cannot be modified."""
        factory = RequestFactory()
        request = factory.get("/admin/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = DataExportLogAdmin(DataExportLog, AdminSite())
        assert admin.has_change_permission(request) is False
