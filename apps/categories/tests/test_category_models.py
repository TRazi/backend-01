"""
Tests for categories app models.
Following Django testing best practices from topics/testing/.
"""

import pytest
from decimal import Decimal
from django.utils import timezone

from categories.models import Category
from households.models import Household
from accounts.models import Account
from transactions.models import Transaction


@pytest.mark.django_db
@pytest.mark.unit
class TestCategoryModel:
    """Test Category model methods and properties."""

    def test_str_method(self):
        """Test __str__ returns category name."""
        household = Household.objects.create(name="Test Household")
        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )
        assert str(category) == "Groceries"

    def test_full_path_property_no_parent(self):
        """Test full_path property for category without parent."""
        household = Household.objects.create(name="Test Household")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        assert category.full_path == "Food"

    def test_full_path_property_with_parent(self):
        """Test full_path property for category with parent."""
        household = Household.objects.create(name="Test Household")
        parent = Category.objects.create(
            household=household, name="Food & Dining", category_type="expense"
        )
        child = Category.objects.create(
            household=household,
            name="Groceries",
            category_type="expense",
            parent=parent,
        )
        assert child.full_path == "Food & Dining > Groceries"

    def test_has_subcategories_property_true(self):
        """Test has_subcategories returns True when subcategories exist."""
        household = Household.objects.create(name="Test Household")
        parent = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        Category.objects.create(
            household=household,
            name="Groceries",
            category_type="expense",
            parent=parent,
        )
        assert parent.has_subcategories is True

    def test_has_subcategories_property_false(self):
        """Test has_subcategories returns False when no subcategories."""
        household = Household.objects.create(name="Test Household")
        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )
        assert category.has_subcategories is False

    def test_get_all_subcategories(self):
        """Test get_all_subcategories returns all nested categories."""
        household = Household.objects.create(name="Test Household")
        parent = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        child1 = Category.objects.create(
            household=household,
            name="Groceries",
            category_type="expense",
            parent=parent,
        )
        child2 = Category.objects.create(
            household=household,
            name="Restaurants",
            category_type="expense",
            parent=parent,
        )

        subcategories = parent.get_all_subcategories()
        assert child1 in subcategories
        assert child2 in subcategories
        assert len(subcategories) == 2

    def test_get_transaction_count(self):
        """Test get_transaction_count returns correct count."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("1000.00")
        )
        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        # Create some transactions
        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("50.00"),
            description="Test transaction 1",
            transaction_type="expense",
            status="completed",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("75.00"),
            description="Test transaction 2",
            transaction_type="expense",
            status="completed",
            date=timezone.now(),
        )

        assert category.get_transaction_count() == 2

    def test_get_total_amount(self):
        """Test get_total_amount calculates sum correctly."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("1000.00")
        )
        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        # Create some transactions
        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("50.00"),
            description="Test transaction 1",
            transaction_type="expense",
            status="completed",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("75.00"),
            description="Test transaction 2",
            transaction_type="expense",
            status="completed",
            date=timezone.now(),
        )

        assert category.get_total_amount() == Decimal("125.00")

    def test_get_usage_stats(self):
        """Test get_usage_stats returns transaction data."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("1000.00")
        )
        category = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        # Create transactions
        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("100.00"),
            description="Test transaction 1",
            transaction_type="expense",
            status="completed",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("50.00"),
            description="Test transaction 2",
            transaction_type="expense",
            status="completed",
            date=timezone.now(),
        )

        stats = category.get_usage_stats()
        assert stats["transaction_count"] == 2
        assert stats["total_amount"] == Decimal("150.00")
        assert stats["has_transactions"] is True
