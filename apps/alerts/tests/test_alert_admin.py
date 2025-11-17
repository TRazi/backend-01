# apps/alerts/tests/test_alert_admin.py
import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from apps.alerts.admin import AlertAdmin
from apps.alerts.models import Alert
from apps.households.models import Household
from apps.users.models import User


@pytest.mark.django_db
class TestAlertAdmin:
    """Test suite for AlertAdmin."""

    def test_list_display_fields(self):
        """Test list_display configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert "title_display" in admin.list_display
        assert "household" in admin.list_display
        assert "alert_type" in admin.list_display
        assert "priority" in admin.list_display
        assert "status" in admin.list_display
        assert "action_required" in admin.list_display
        assert "sent_via_email" in admin.list_display
        assert "sent_via_push" in admin.list_display
        assert "created_at" in admin.list_display

    def test_list_filter_fields(self):
        """Test list_filter configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert "alert_type" in admin.list_filter
        assert "priority" in admin.list_filter
        assert "status" in admin.list_filter
        assert "action_required" in admin.list_filter
        assert "sent_via_email" in admin.list_filter
        assert "sent_via_push" in admin.list_filter
        assert "created_at" in admin.list_filter

    def test_search_fields(self):
        """Test search_fields configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert "title" in admin.search_fields
        assert "message" in admin.search_fields
        assert "household__name" in admin.search_fields

    def test_autocomplete_fields(self):
        """Test autocomplete_fields configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert "household" in admin.autocomplete_fields
        assert "related_budget" in admin.autocomplete_fields
        assert "related_bill" in admin.autocomplete_fields
        assert "related_account" in admin.autocomplete_fields
        assert "related_goal" in admin.autocomplete_fields
        assert "dismissed_by" in admin.autocomplete_fields

    def test_date_hierarchy(self):
        """Test date_hierarchy configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert admin.date_hierarchy == "created_at"

    def test_readonly_fields(self):
        """Test readonly_fields configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_title_display_with_title(self):
        """Test title_display shows title when present."""
        household = Household.objects.create(name="Test Household")
        alert = Alert.objects.create(
            household=household,
            title="Important Alert",
            message="This is a test message",
            alert_type="budget_exceeded",
            priority="high",
        )

        admin = AlertAdmin(Alert, AdminSite())
        display = admin.title_display(alert)

        assert display == "Important Alert"

    def test_title_display_without_title(self):
        """Test title_display truncates message when no title."""
        household = Household.objects.create(name="Test Household")
        long_message = "This is a very long message that should be truncated to only show the first 50 characters"
        alert = Alert.objects.create(
            household=household,
            message=long_message,
            alert_type="bill_due",
            priority="medium",
        )

        admin = AlertAdmin(Alert, AdminSite())
        display = admin.title_display(alert)

        assert len(display) == 53  # 50 chars + "..."
        assert display.endswith("...")
        assert long_message[:50] in display

    def test_title_display_short_description(self):
        """Test title_display column name."""
        admin = AlertAdmin(Alert, AdminSite())
        assert admin.title_display.short_description == "Title"

    def test_queryset_optimization(self):
        """Test get_queryset uses select_related for performance."""
        household = Household.objects.create(name="Test Household")
        Alert.objects.create(
            household=household,
            message="Test alert",
            alert_type="payment_reminder",
            priority="low",
        )

        admin = AlertAdmin(Alert, AdminSite())
        request = RequestFactory().get("/admin/alerts/alert/")
        queryset = admin.get_queryset(request)

        # Check that select_related is applied
        assert "household" in queryset.query.select_related
        assert "related_budget" in queryset.query.select_related
        assert "related_bill" in queryset.query.select_related
        assert "related_account" in queryset.query.select_related
        assert "related_goal" in queryset.query.select_related
        assert "dismissed_by" in queryset.query.select_related

    def test_fieldsets_structure(self):
        """Test fieldsets configuration."""
        admin = AlertAdmin(Alert, AdminSite())
        assert len(admin.fieldsets) == 7

        # Check Alert Information section
        assert admin.fieldsets[0][0] == "Alert Information"
        assert "household" in admin.fieldsets[0][1]["fields"]
        assert "alert_type" in admin.fieldsets[0][1]["fields"]
        assert "priority" in admin.fieldsets[0][1]["fields"]

        # Check Trigger Details section (collapsed)
        assert admin.fieldsets[1][0] == "Trigger Details"
        assert "collapse" in admin.fieldsets[1][1]["classes"]

        # Check Related Objects section (collapsed)
        assert admin.fieldsets[2][0] == "Related Objects"
        assert "collapse" in admin.fieldsets[2][1]["classes"]
        assert "related_budget" in admin.fieldsets[2][1]["fields"]

        # Check Action section
        assert admin.fieldsets[3][0] == "Action"
        assert "action_required" in admin.fieldsets[3][1]["fields"]

        # Check Notifications section
        assert admin.fieldsets[4][0] == "Notifications"
        assert "sent_via_email" in admin.fieldsets[4][1]["fields"]

        # Check Dismissal section (collapsed)
        assert admin.fieldsets[5][0] == "Dismissal"
        assert "collapse" in admin.fieldsets[5][1]["classes"]

        # Check Timestamps section (collapsed)
        assert admin.fieldsets[6][0] == "Timestamps"
        assert "collapse" in admin.fieldsets[6][1]["classes"]
