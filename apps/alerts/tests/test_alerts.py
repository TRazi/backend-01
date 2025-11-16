"""
Tests for alerts models and serializers.
Tests alert creation, validation, properties, and serialization.
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from alerts.models import Alert
from alerts.serializers import AlertSerializer, AlertDismissSerializer
from alerts.enums import (
    ALERT_TYPE_CHOICES,
    ALERT_PRIORITY_CHOICES,
    ALERT_STATUS_CHOICES,
)
from households.models import Household
from budgets.models import Budget
from accounts.models import Account
from goals.models import Goal
from users.models import User


@pytest.mark.django_db
class TestAlertModel:
    """Test Alert model functionality."""

    def setup_method(self):
        """Set up test data."""
        self.household = Household.objects.create(
            name="Test Household", household_type="fam"
        )

        from datetime import timedelta

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        self.budget = Budget.objects.create(
            household=self.household,
            name="Groceries",
            total_amount=Decimal("500.00"),
            start_date=start_date,
            end_date=end_date,
        )

        self.account = Account.objects.create(
            household=self.household, account_type="chq", balance=Decimal("1000.00")
        )

    def test_alert_creation(self):
        """Test creating a basic alert."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            priority="high",
            message="Budget warning: 80% spent",
            title="Budget Alert",
        )

        assert alert.id is not None
        assert alert.household == self.household
        assert alert.alert_type == "budget_warning"
        assert alert.priority == "high"
        assert alert.status == "active"

    def test_alert_with_related_budget(self):
        """Test alert with related budget reference."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Budget exceeded",
            related_budget=self.budget,
            trigger_value=Decimal("80.00"),
        )

        assert alert.related_budget == self.budget
        assert alert.trigger_value == Decimal("80.00")

    def test_alert_with_related_account(self):
        """Test alert with related account reference."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="low_balance",
            message="Low balance warning",
            related_account=self.account,
            trigger_value=Decimal("100.00"),
        )

        assert alert.related_account == self.account

    def test_alert_is_active_property_true(self):
        """Test is_active property returns True for active alerts."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            status="active",
        )

        assert alert.is_active is True

    def test_alert_is_active_property_false(self):
        """Test is_active property returns False for non-active alerts."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            status="dismissed",
        )

        assert alert.is_active is False

    def test_alert_is_high_priority_urgent(self):
        """Test is_high_priority returns True for urgent priority."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            priority="urgent",
        )

        assert alert.is_high_priority is True

    def test_alert_is_high_priority_high(self):
        """Test is_high_priority returns True for high priority."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            priority="high",
        )

        assert alert.is_high_priority is True

    def test_alert_is_high_priority_medium(self):
        """Test is_high_priority returns False for medium priority."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            priority="medium",
        )

        assert alert.is_high_priority is False

    def test_alert_is_high_priority_low(self):
        """Test is_high_priority returns False for low priority."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            priority="low",
        )

        assert alert.is_high_priority is False

    def test_alert_str_representation(self):
        """Test string representation of alert."""
        alert = Alert.objects.create(
            household=self.household, alert_type="budget_warning", message="Test alert"
        )

        expected = f"{alert.get_alert_type_display()} - {self.household.name}"
        assert str(alert) == expected

    def test_alert_clean_validates_budget_household(self):
        """Test clean() validates related budget belongs to same household."""
        other_household = Household.objects.create(
            name="Other Household", household_type="fam"
        )

        from datetime import timedelta

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        other_budget = Budget.objects.create(
            household=other_household,
            name="Other Budget",
            total_amount=Decimal("100.00"),
            start_date=start_date,
            end_date=end_date,
        )

        alert = Alert(
            household=self.household,
            alert_type="budget_warning",
            message="Test",
            related_budget=other_budget,
        )

        with pytest.raises(ValidationError) as exc:
            alert.clean()

        assert "Related budget must belong to the same household" in str(exc.value)

    def test_alert_clean_validates_account_household(self):
        """Test clean() validates related account belongs to same household."""
        other_household = Household.objects.create(
            name="Other Household", household_type="fam"
        )

        other_account = Account.objects.create(
            household=other_household, account_type="chq", balance=Decimal("100.00")
        )

        alert = Alert(
            household=self.household,
            alert_type="low_balance",
            message="Test",
            related_account=other_account,
        )

        with pytest.raises(ValidationError) as exc:
            alert.clean()

        assert "Related account must belong to the same household" in str(exc.value)

    def test_alert_clean_validates_goal_household(self):
        """Test clean() validates related goal belongs to same household."""
        other_household = Household.objects.create(
            name="Other Household", household_type="fam"
        )

        Goal.objects.create(
            household=self.household,
            name="My Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=timezone.now().date(),
        )

        other_goal = Goal.objects.create(
            household=other_household,
            name="Other Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=timezone.now().date(),
        )

        alert = Alert(
            household=self.household,
            alert_type="goal_milestone",
            message="Test",
            related_goal=other_goal,
        )

        with pytest.raises(ValidationError) as exc:
            alert.clean()

        assert "Related goal must belong to the same household" in str(exc.value)

    def test_alert_action_tracking(self):
        """Test action tracking fields."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            action_required=True,
            action_url="https://example.com/budget/123",
        )

        assert alert.action_required is True
        assert alert.action_url == "https://example.com/budget/123"

    def test_alert_notification_tracking(self):
        """Test notification tracking fields."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            sent_via_email=True,
            sent_via_push=False,
        )

        assert alert.sent_via_email is True
        assert alert.sent_via_push is False

    def test_alert_dismissal_tracking(self):
        """Test dismissal tracking fields."""
        user = User.objects.create_user(
            email="user@example.com", password="TestPass123!"
        )

        alert = Alert.objects.create(
            household=self.household, alert_type="budget_warning", message="Test alert"
        )

        now = timezone.now()
        alert.dismissed_at = now
        alert.dismissed_by = user
        alert.save()

        alert.refresh_from_db()

        assert alert.dismissed_at == now
        assert alert.dismissed_by == user


@pytest.mark.django_db
class TestAlertSerializer:
    """Test AlertSerializer functionality."""

    def setup_method(self):
        """Set up test data."""
        self.household = Household.objects.create(
            name="Test Household", household_type="fam"
        )

        from datetime import timedelta

        start_date = timezone.now().date()
        end_date = start_date + timedelta(days=30)

        self.budget = Budget.objects.create(
            household=self.household,
            name="Groceries",
            total_amount=Decimal("500.00"),
            start_date=start_date,
            end_date=end_date,
        )

    def test_alert_serializer_fields(self):
        """Test AlertSerializer includes all expected fields."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            priority="high",
            message="Test alert",
            title="Alert Title",
        )

        serializer = AlertSerializer(alert)
        data = serializer.data

        # Check required fields
        assert "id" in data
        assert "household" in data
        assert "alert_type" in data
        assert "priority" in data
        assert "status" in data
        assert "message" in data
        assert "title" in data

        # Check computed fields
        assert "is_active" in data
        assert "is_high_priority" in data

    def test_alert_serializer_read_only_fields(self):
        """Test AlertSerializer has all fields as read-only."""
        serializer = AlertSerializer()

        # All fields should be read-only
        assert len(serializer.Meta.read_only_fields) == len(serializer.Meta.fields)

    def test_alert_serializer_is_active_field(self):
        """Test is_active computed field in serializer."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            status="active",
        )

        serializer = AlertSerializer(alert)

        assert serializer.data["is_active"] is True

    def test_alert_serializer_is_high_priority_field(self):
        """Test is_high_priority computed field in serializer."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            priority="urgent",
        )

        serializer = AlertSerializer(alert)

        assert serializer.data["is_high_priority"] is True

    def test_alert_serializer_with_related_budget(self):
        """Test AlertSerializer includes related budget ID."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            related_budget=self.budget,
        )

        serializer = AlertSerializer(alert)

        assert serializer.data["related_budget"] == self.budget.id

    def test_alert_serializer_trigger_value(self):
        """Test AlertSerializer includes trigger_value."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            trigger_value=Decimal("75.50"),
        )

        serializer = AlertSerializer(alert)

        assert serializer.data["trigger_value"] == "75.50"


@pytest.mark.django_db
class TestAlertDismissSerializer:
    """Test AlertDismissSerializer functionality."""

    def setup_method(self):
        """Set up test data."""
        self.factory = APIRequestFactory()

        self.user = User.objects.create_user(
            email="user@example.com", password="TestPass123!"
        )

        self.household = Household.objects.create(
            name="Test Household", household_type="fam"
        )

    def test_dismiss_serializer_updates_status(self):
        """Test AlertDismissSerializer sets status to dismissed."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            status="active",
        )

        request = self.factory.post("/api/alerts/123/dismiss/")
        request.user = self.user

        serializer = AlertDismissSerializer(
            instance=alert, data={}, context={"request": request}
        )

        assert serializer.is_valid()
        updated_alert = serializer.save()

        assert updated_alert.status == "dismissed"

    def test_dismiss_serializer_sets_dismissed_by(self):
        """Test AlertDismissSerializer sets dismissed_by to current user."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            status="active",
        )

        request = self.factory.post("/api/alerts/123/dismiss/")
        request.user = self.user

        serializer = AlertDismissSerializer(
            instance=alert, data={}, context={"request": request}
        )

        assert serializer.is_valid()
        updated_alert = serializer.save()

        assert updated_alert.dismissed_by == self.user

    def test_dismiss_serializer_saves_to_database(self):
        """Test AlertDismissSerializer persists changes to database."""
        alert = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Test alert",
            status="active",
        )

        request = self.factory.post("/api/alerts/123/dismiss/")
        request.user = self.user

        serializer = AlertDismissSerializer(
            instance=alert, data={}, context={"request": request}
        )

        serializer.is_valid()
        serializer.save()

        # Refresh from database
        alert.refresh_from_db()

        assert alert.status == "dismissed"
        assert alert.dismissed_by == self.user


@pytest.mark.django_db
class TestAlertOrdering:
    """Test Alert model ordering."""

    def setup_method(self):
        """Set up test data."""
        self.household = Household.objects.create(
            name="Test Household", household_type="fam"
        )

    def test_alerts_ordered_by_created_at_desc(self):
        """Test alerts are ordered by created_at descending."""
        # Create alerts with slight time differences
        alert1 = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Alert 1",
            priority="medium",
        )

        alert2 = Alert.objects.create(
            household=self.household,
            alert_type="budget_warning",
            message="Alert 2",
            priority="medium",
        )

        alerts = Alert.objects.all()

        # Most recent should be first
        assert alerts[0].id == alert2.id
        assert alerts[1].id == alert1.id

    def test_alerts_ordered_by_priority_desc(self):
        """Test alerts are secondarily ordered by priority."""
        # This test verifies that the Meta.ordering includes priority
        assert "priority" in Alert._meta.ordering or "-priority" in Alert._meta.ordering
