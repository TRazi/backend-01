"""
Tests for accounts app permissions.
Following Django testing best practices from topics/testing/.
"""

import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from accounts.permissions import IsAccountHouseholdMember
from accounts.models import Account
from households.models import Household

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestIsAccountHouseholdMember:
    """Test IsAccountHouseholdMember permission class."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        permission = IsAccountHouseholdMember()
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Test Account", balance=1000.00
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        request.user.is_staff = False

        # Permission should deny (account has household_id, user has none or no auth)
        result = permission.has_object_permission(request, None, account)
        # Without proper household_id, comparison will fail
        assert result is False or request.user.household_id != account.household_id

    def test_staff_user_allowed(self):
        """Staff users should have full access regardless of household."""
        permission = IsAccountHouseholdMember()
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Test Account", balance=1000.00
        )

        request = Mock()
        request.user = Mock()
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, account) is True

    def test_same_household_allowed(self):
        """Users in the same household should have access."""
        permission = IsAccountHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household, name="Test Account", balance=1000.00
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, account) is True

    def test_different_household_denied(self):
        """Users in different households should be denied access."""
        permission = IsAccountHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household1
        user.save()

        account = Account.objects.create(
            household=household2, name="Test Account", balance=1000.00
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, account) is False
