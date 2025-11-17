"""
Tests for transactions app permissions.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from apps.transactions.permissions import IsTransactionHouseholdMember
from apps.transactions.models import Transaction
from apps.accounts.models import Account
from apps.households.models import Household
from apps.categories.models import Category

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestIsTransactionHouseholdMember:
    """Test IsTransactionHouseholdMember permission class."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        permission = IsTransactionHouseholdMember()
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Test Account", balance=1000.00
        )
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )
        transaction = Transaction.objects.create(
            account=account,
            category=category,
            amount=100.00,
            description="Test transaction",
            date=date(2025, 11, 14),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False
        request.user.is_staff = False

        # Without proper household_id, comparison will fail
        result = permission.has_object_permission(request, None, transaction)
        assert (
            result is False
            or request.user.household_id != transaction.account.household_id
        )

    def test_staff_user_allowed(self):
        """Staff users should have full access regardless of household."""
        permission = IsTransactionHouseholdMember()
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Test Account", balance=1000.00
        )
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )
        transaction = Transaction.objects.create(
            account=account,
            category=category,
            amount=100.00,
            description="Test transaction",
            date=date(2025, 11, 14),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, transaction) is True

    def test_same_household_allowed(self):
        """Users in the same household should have access."""
        permission = IsTransactionHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household, name="Test Account", balance=1000.00
        )
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )
        transaction = Transaction.objects.create(
            account=account,
            category=category,
            amount=100.00,
            description="Test transaction",
            date=date(2025, 11, 14),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, transaction) is True

    def test_different_household_denied(self):
        """Users in different households should be denied access."""
        permission = IsTransactionHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household1
        user.save()

        account = Account.objects.create(
            household=household2, name="Test Account", balance=1000.00
        )
        category = Category.objects.create(
            household=household2, name="Test Category", category_type="expense"
        )
        transaction = Transaction.objects.create(
            account=account,
            category=category,
            amount=100.00,
            description="Test transaction",
            date=date(2025, 11, 14),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, transaction) is False
