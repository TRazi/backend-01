"""Tests for budget permissions."""

import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from apps.budgets.models import Budget, BudgetItem
from apps.budgets.permissions import IsBudgetHouseholdMember, IsBudgetItemHouseholdMember
from apps.households.models import Household
from apps.categories.models import Category

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestIsBudgetHouseholdMember:
    """Test IsBudgetHouseholdMember permission."""

    def test_unauthenticated_user_denied(self):
        """Test unauthenticated users are denied."""
        permission = IsBudgetHouseholdMember()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )

        assert not permission.has_object_permission(request, None, budget)

    def test_staff_user_allowed(self):
        """Test staff users are always allowed."""
        permission = IsBudgetHouseholdMember()
        user = User.objects.create_user(email="staff@test.com", password="test")
        user.is_staff = True
        user.save()

        request = Mock()
        request.user = user

        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )

        assert permission.has_object_permission(request, None, budget)

    def test_same_household_allowed(self):
        """Test users from same household are allowed."""
        permission = IsBudgetHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="test")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )

        assert permission.has_object_permission(request, None, budget)

    def test_different_household_denied(self):
        """Test users from different household are denied."""
        permission = IsBudgetHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        user = User.objects.create_user(email="user@test.com", password="test")
        user.household = household1
        user.save()

        request = Mock()
        request.user = user

        budget = Budget.objects.create(
            household=household2,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )

        assert not permission.has_object_permission(request, None, budget)


@pytest.mark.django_db
@pytest.mark.unit
class TestIsBudgetItemHouseholdMember:
    """Test IsBudgetItemHouseholdMember permission."""

    def test_unauthenticated_user_denied(self):
        """Test unauthenticated users are denied."""
        permission = IsBudgetItemHouseholdMember()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Test Item", amount=100, category=category
        )

        assert not permission.has_object_permission(request, None, item)

    def test_staff_user_allowed(self):
        """Test staff users are always allowed."""
        permission = IsBudgetItemHouseholdMember()
        user = User.objects.create_user(email="staff@test.com", password="test")
        user.is_staff = True
        user.save()

        request = Mock()
        request.user = user

        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Test Item", amount=100, category=category
        )

        assert permission.has_object_permission(request, None, item)

    def test_same_household_allowed(self):
        """Test users from same household are allowed."""
        permission = IsBudgetItemHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="test")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Test Item", amount=100, category=category
        )

        assert permission.has_object_permission(request, None, item)

    def test_different_household_denied(self):
        """Test users from different household are denied."""
        permission = IsBudgetItemHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        user = User.objects.create_user(email="user@test.com", password="test")
        user.household = household1
        user.save()

        request = Mock()
        request.user = user

        budget = Budget.objects.create(
            household=household2,
            name="Test Budget",
            start_date="2025-01-01",
            end_date="2025-12-31",
            total_amount=1000,
        )
        category = Category.objects.create(
            household=household2, name="Test Category", category_type="expense"
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Test Item", amount=100, category=category
        )

        assert not permission.has_object_permission(request, None, item)
