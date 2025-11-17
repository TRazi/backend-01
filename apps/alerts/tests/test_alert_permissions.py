"""
Tests for alerts app permissions.
Following Django testing best practices from topics/testing/.
"""

import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from apps.alerts.permissions import IsAlertHouseholdMember
from apps.alerts.models import Alert
from apps.households.models import Household

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestIsAlertHouseholdMember:
    """Test IsAlertHouseholdMember permission class."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        permission = IsAlertHouseholdMember()
        household = Household.objects.create(name="Test Household")
        alert = Alert.objects.create(
            household=household,
            title="Test Alert",
            message="This is a test alert",
            alert_type="info",
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert permission.has_object_permission(request, None, alert) is False

    def test_staff_user_allowed(self):
        """Staff users should have full access regardless of household."""
        permission = IsAlertHouseholdMember()
        household = Household.objects.create(name="Test Household")
        alert = Alert.objects.create(
            household=household,
            title="Test Alert",
            message="This is a test alert",
            alert_type="info",
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, alert) is True

    def test_same_household_allowed(self):
        """Users in the same household should have access."""
        permission = IsAlertHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household
        user.save()

        alert = Alert.objects.create(
            household=household,
            title="Test Alert",
            message="This is a test alert",
            alert_type="info",
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, alert) is True

    def test_different_household_denied(self):
        """Users in different households should be denied access."""
        permission = IsAlertHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household1
        user.save()

        alert = Alert.objects.create(
            household=household2,
            title="Test Alert",
            message="This is a test alert",
            alert_type="info",
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, alert) is False
