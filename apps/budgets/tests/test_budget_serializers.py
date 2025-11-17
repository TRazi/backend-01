"""
Test suite for budget serializers.
Tests validation logic and serialization behavior.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from apps.budgets.models import Budget, BudgetItem
from apps.budgets.serializers import (
    BudgetSerializer,
    BudgetItemSerializer,
    BudgetItemCreateSerializer,
)
from apps.households.models import Household, Membership
from apps.categories.models import Category

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetSerializer:
    """Test BudgetSerializer validation and behavior."""

    def test_validate_end_date_before_start_date(self):
        """Test validation fails when end_date is before start_date."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "Test Budget",
                "start_date": date.today(),
                "end_date": date.today() - timedelta(days=1),
                "total_amount": Decimal("1000.00"),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "end_date cannot be before start_date" in str(
            serializer.errors["non_field_errors"]
        )

    def test_validate_negative_total_amount(self):
        """Test validation fails for negative total_amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "Test Budget",
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=30),
                "total_amount": Decimal("-100.00"),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "total_amount must be positive" in str(
            serializer.errors["non_field_errors"]
        )

    def test_validate_zero_total_amount(self):
        """Test validation fails for zero total_amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "Test Budget",
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=30),
                "total_amount": Decimal("0.00"),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "total_amount must be positive" in str(
            serializer.errors["non_field_errors"]
        )

    def test_create_sets_household_from_user(self):
        """Test that create() automatically sets household from request.user."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "Test Budget",
                "start_date": date.today(),
                "end_date": date.today() + timedelta(days=30),
                "total_amount": Decimal("1000.00"),
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        budget = serializer.save()

        assert budget.household == household
        assert budget.name == "Test Budget"

    def test_serializer_includes_computed_fields(self):
        """Test that serializer includes computed fields from model."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        serializer = BudgetSerializer(budget)

        assert "total_spent" in serializer.data
        assert "total_remaining" in serializer.data
        assert "utilization_percentage" in serializer.data
        assert "is_active" in serializer.data
        assert "is_expired" in serializer.data
        assert "days_remaining" in serializer.data


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetItemSerializer:
    """Test BudgetItemSerializer behavior."""

    def test_serializer_includes_computed_fields(self):
        """Test that serializer includes computed fields."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        item = BudgetItem.objects.create(
            budget=budget, name="Groceries", amount=Decimal("300.00"), category=category
        )

        serializer = BudgetItemSerializer(item)

        assert "utilization_percentage" in serializer.data
        assert "remaining_amount" in serializer.data
        # Decimal formatting may vary
        assert str(serializer.data["utilization_percentage"]) in ["0.00", "0E+2", "0"]
        assert str(serializer.data["remaining_amount"]) in ["300", "300.00"]

    def test_serializer_get_methods_called(self):
        """Test BudgetItemSerializer get methods are called."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        item = BudgetItem.objects.create(
            budget=budget, name="Groceries", amount=Decimal("300.00"), category=category
        )

        serializer = BudgetItemSerializer(item)

        # Test get methods are called
        assert (
            serializer.get_utilization_percentage(item)
            == item.get_utilization_percentage()
        )
        assert serializer.get_remaining_amount(item) == item.get_remaining()


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetItemCreateSerializer:
    """Test BudgetItemCreateSerializer behavior."""

    def test_create_sets_budget_from_context(self):
        """Test that create() sets budget from context."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        serializer = BudgetItemCreateSerializer(
            data={
                "name": "Groceries",
                "amount": Decimal("300.00"),
                "category": category.id,
                "notes": "Monthly grocery budget",
            },
            context={"budget": budget},
        )

        assert serializer.is_valid()
        item = serializer.save()

        assert item.budget == budget
        assert item.name == "Groceries"
        assert item.amount == Decimal("300.00")


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetSerializerEdgeCases:
    """Test BudgetSerializer edge cases."""

    def test_budget_with_zero_amount(self):
        """Test budget with zero total amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Zero Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("0.00"),
        )

        serializer = BudgetSerializer(budget)
        assert serializer.data["total_amount"] in ["0", "0.00"]

    def test_budget_with_large_amount(self):
        """Test budget with large amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Large Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("999999.99"),
        )

        serializer = BudgetSerializer(budget)
        assert "999999" in str(serializer.data["total_amount"])

    def test_budget_item_serializer_includes_category(self):
        """Test that budget item serializer includes category details."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )

        budget_item = BudgetItem.objects.create(
            budget=budget,
            name="Food Budget",
            category=category,
            amount=Decimal("200.00"),
        )

        serializer = BudgetItemSerializer(budget_item)
        assert "category" in serializer.data
        assert serializer.data["amount"] in ["200", "200.00"]

    def test_budget_serializer_with_multiple_items(self):
        """Test budget with multiple budget items."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        budget = Budget.objects.create(
            household=household,
            name="Multi-Item Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        category1 = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        category2 = Category.objects.create(
            household=household, name="Transport", category_type="expense"
        )

        BudgetItem.objects.create(
            budget=budget, name="Food", category=category1, amount=Decimal("400.00")
        )
        BudgetItem.objects.create(
            budget=budget,
            name="Transport",
            category=category2,
            amount=Decimal("200.00"),
        )

        serializer = BudgetSerializer(budget)
        assert len(serializer.data["items"]) == 2


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetSerializerValidation:
    """Test Budget serializer validation."""

    def test_budget_end_date_before_start_date_validation(self):
        """Test validation prevents end_date before start_date."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        from unittest.mock import Mock

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "Invalid Budget",
                "start_date": "2025-12-01",
                "end_date": "2025-11-01",
                "total_amount": "1000.00",
                "cycle_type": "monthly",
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_budget_negative_amount_validation(self):
        """Test validation prevents negative total_amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        from unittest.mock import Mock

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "Negative Budget",
                "start_date": "2025-11-01",
                "end_date": "2025-11-30",
                "total_amount": "-100.00",
                "cycle_type": "monthly",
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_budget_item_create_serializer(self):
        """Test BudgetItemCreateSerializer."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        from budgets.serializers import BudgetItemCreateSerializer

        serializer = BudgetItemCreateSerializer(
            data={
                "name": "Groceries",
                "amount": "300.00",
                "category": category.id,
                "notes": "Weekly groceries",
            },
            context={"budget": budget},
        )

        assert serializer.is_valid()
        item = serializer.save()
        assert item.budget == budget
        assert item.name == "Groceries"

    def test_budget_serializer_computed_methods(self):
        """Test BudgetSerializer includes computed methods."""
        from budgets.serializers import BudgetSerializer

        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            total_amount=Decimal("1000.00"),
        )

        serializer = BudgetSerializer(budget)
        data = serializer.data

        # Check computed fields are present
        assert "total_spent" in data
        assert "total_remaining" in data
        assert "utilization_percentage" in data
        assert "is_active" in data
        assert "is_expired" in data
        assert "days_remaining" in data

    def test_budget_serializer_create_assigns_household(self):
        """Test BudgetSerializer.create assigns household from user."""
        from budgets.serializers import BudgetSerializer

        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")
        user.household = household
        user.save()

        from unittest.mock import Mock

        request = Mock()
        request.user = user

        serializer = BudgetSerializer(
            data={
                "name": "New Budget",
                "start_date": "2025-02-01",
                "end_date": "2025-02-28",
                "total_amount": "1500.00",
                "cycle_type": "monthly",
                "status": "active",
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        budget = serializer.save()
        assert budget.household == household

    def test_budget_serializer_get_methods_return_values(self):
        """Test BudgetSerializer get methods return correct values."""
        from budgets.serializers import BudgetSerializer

        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
        )

        serializer = BudgetSerializer(budget)

        # Test get methods are called and return values
        assert serializer.get_total_spent(budget) == budget.get_total_spent()
        assert serializer.get_total_remaining(budget) == budget.get_total_remaining()
        assert (
            serializer.get_utilization_percentage(budget)
            == budget.get_utilization_percentage()
        )
