"""
Tests for budgets app models.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError

from budgets.models import Budget, BudgetItem
from households.models import Household
from categories.models import Category
from accounts.models import Account
from transactions.models import Transaction


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetModel:
    """Test Budget model methods and properties."""

    def test_str_method(self):
        """Test __str__ method returns budget name with household."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="January Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        assert str(budget) == "January Budget (Test Household)"

    def test_clean_validates_date_range(self):
        """Test clean raises error when start_date >= end_date."""
        household = Household.objects.create(name="Test Household")
        budget = Budget(
            household=household,
            name="Invalid Budget",
            total_amount=Decimal("1000.00"),
            start_date=date(2025, 1, 31),
            end_date=date(2025, 1, 1),  # Before start_date
        )
        with pytest.raises(ValidationError, match="start_date must be before end_date"):
            budget.clean()

    def test_clean_validates_positive_total_amount(self):
        """Test clean raises error for non-positive total_amount."""
        household = Household.objects.create(name="Test Household")
        budget = Budget(
            household=household,
            name="Zero Budget",
            total_amount=Decimal("0.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        with pytest.raises(
            ValidationError, match="total_amount must be greater than zero"
        ):
            budget.clean()

    def test_clean_validates_alert_threshold_range(self):
        """Test clean validates alert_threshold is between 0 and 100."""
        household = Household.objects.create(name="Test Household")
        budget = Budget(
            household=household,
            name="Invalid Alert Budget",
            total_amount=Decimal("1000.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            alert_threshold=150,  # Invalid: > 100
        )
        with pytest.raises(
            ValidationError, match="alert_threshold must be between 0 and 100"
        ):
            budget.clean()

    def test_is_active_property_true(self):
        """Test is_active returns True for active budget in current period."""
        household = Household.objects.create(name="Test Household")
        today = date.today()
        budget = Budget.objects.create(
            household=household,
            name="Current Budget",
            total_amount=Decimal("2000.00"),
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=25),
            status="active",
        )
        assert budget.is_active is True

    def test_is_active_property_false_inactive_status(self):
        """Test is_active returns False for inactive budget."""
        household = Household.objects.create(name="Test Household")
        today = date.today()
        budget = Budget.objects.create(
            household=household,
            name="Inactive Budget",
            total_amount=Decimal("2000.00"),
            start_date=today - timedelta(days=5),
            end_date=today + timedelta(days=25),
            status="completed",
        )
        assert budget.is_active is False

    def test_is_expired_property_true(self):
        """Test is_expired returns True for past budget."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Expired Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert budget.is_expired is True

    def test_is_expired_property_false(self):
        """Test is_expired returns False for future budget."""
        household = Household.objects.create(name="Test Household")
        today = date.today()
        budget = Budget.objects.create(
            household=household,
            name="Future Budget",
            total_amount=Decimal("2000.00"),
            start_date=today,
            end_date=today + timedelta(days=30),
        )
        assert budget.is_expired is False

    def test_days_remaining_property_positive(self):
        """Test days_remaining returns positive value for active budget."""
        household = Household.objects.create(name="Test Household")
        today = date.today()
        budget = Budget.objects.create(
            household=household,
            name="Active Budget",
            total_amount=Decimal("2000.00"),
            start_date=today,
            end_date=today + timedelta(days=10),
        )
        # Allow for off-by-one due to date boundary timing
        assert budget.days_remaining in [10, 11]

    def test_days_remaining_property_zero_for_expired(self):
        """Test days_remaining returns 0 for expired budget."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Expired Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        assert budget.days_remaining == 0

    def test_get_total_spent_with_transactions(self):
        """Test get_total_spent calculates correctly."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )

        # Create transactions within budget period
        Transaction.objects.create(
            account=account,
            amount=Decimal("-100.00"),
            description="Expense 1",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )
        Transaction.objects.create(
            account=account,
            amount=Decimal("-50.00"),
            description="Expense 2",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 20)),
        )

        # Should return absolute value of total
        assert budget.get_total_spent() == Decimal("150.00")

    def test_get_total_spent_zero_no_transactions(self):
        """Test get_total_spent returns 0 when no transactions."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Empty Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        assert budget.get_total_spent() == 0

    def test_get_total_remaining(self):
        """Test get_total_remaining calculates correctly."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )

        Transaction.objects.create(
            account=account,
            amount=Decimal("-500.00"),
            description="Expense",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert budget.get_total_remaining() == Decimal("1500.00")

    def test_get_utilization_percentage(self):
        """Test get_utilization_percentage calculates correctly."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )

        Transaction.objects.create(
            account=account,
            amount=Decimal("-1000.00"),
            description="Expense",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        # 1000 / 2000 * 100 = 50%
        assert budget.get_utilization_percentage() == pytest.approx(50.0)

    def test_get_utilization_percentage_zero_budget(self):
        """Test get_utilization_percentage returns 0 for zero budget."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            total_amount=Decimal("1.00"),  # Will be set to 0 for this test logic
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        # Directly test the calculation logic
        budget.total_amount = 0
        assert budget.get_utilization_percentage() == 0

    def test_is_over_budget_true(self):
        """Test is_over_budget returns True when exceeded."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Over Budget",
            total_amount=Decimal("100.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )

        Transaction.objects.create(
            account=account,
            amount=Decimal("-150.00"),
            description="Overspending",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert budget.is_over_budget() is True

    def test_is_over_budget_false(self):
        """Test is_over_budget returns False when under budget."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Under Budget",
            total_amount=Decimal("1000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )

        Transaction.objects.create(
            account=account,
            amount=Decimal("-100.00"),
            description="Small expense",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert budget.is_over_budget() is False

    def test_should_alert_true(self):
        """Test should_alert returns True when threshold reached."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Alert Budget",
            total_amount=Decimal("1000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
            alert_threshold=80,
        )

        Transaction.objects.create(
            account=account,
            amount=Decimal("-850.00"),  # 85% of budget
            description="High expense",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert budget.should_alert() is True

    def test_should_alert_false(self):
        """Test should_alert returns False when below threshold."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        budget = Budget.objects.create(
            household=household,
            name="Safe Budget",
            total_amount=Decimal("1000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
            alert_threshold=80,
        )

        Transaction.objects.create(
            account=account,
            amount=Decimal("-500.00"),  # 50% of budget
            description="Normal expense",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert budget.should_alert() is False


@pytest.mark.django_db
@pytest.mark.unit
class TestBudgetItemModel:
    """Test BudgetItem model methods and properties."""

    def test_str_method(self):
        """Test __str__ method returns formatted string."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="January Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Groceries", amount=Decimal("500.00")
        )
        assert str(item) == "Groceries - $500.00 (January Budget)"

    def test_clean_validates_positive_amount(self):
        """Test clean raises error for non-positive amount."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        item = BudgetItem(budget=budget, name="Invalid", amount=Decimal("-100.00"))
        with pytest.raises(ValidationError, match="amount must be greater than zero"):
            item.clean()

    def test_clean_validates_category_household(self):
        """Test clean validates category belongs to same household."""
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        budget = Budget.objects.create(
            household=household1,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
        )
        category = Category.objects.create(household=household2, name="Food")
        item = BudgetItem(
            budget=budget, name="Food Item", amount=Decimal("100.00"), category=category
        )
        with pytest.raises(
            ValidationError,
            match="Category must belong to the same household as budget",
        ):
            item.clean()

    def test_get_spent_with_category(self):
        """Test get_spent calculates correctly for categorized item."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        category = Category.objects.create(household=household, name="Groceries")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Groceries", amount=Decimal("500.00"), category=category
        )

        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("-150.00"),
            description="Grocery shopping",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert item.get_spent() == Decimal("150.00")

    def test_get_spent_no_category(self):
        """Test get_spent returns 0 when no category assigned."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Uncategorized", amount=Decimal("500.00")
        )
        assert item.get_spent() == 0

    def test_get_remaining(self):
        """Test get_remaining calculates correctly."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        category = Category.objects.create(household=household, name="Dining")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Dining", amount=Decimal("300.00"), category=category
        )

        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("-100.00"),
            description="Restaurant",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert item.get_remaining() == Decimal("200.00")

    def test_get_utilization_percentage(self):
        """Test get_utilization_percentage calculates correctly."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        category = Category.objects.create(household=household, name="Entertainment")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget,
            name="Entertainment",
            amount=Decimal("400.00"),
            category=category,
        )

        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("-200.00"),
            description="Movies",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        # 200 / 400 * 100 = 50%
        assert item.get_utilization_percentage() == pytest.approx(50.0)

    def test_get_utilization_percentage_zero_amount(self):
        """Test get_utilization_percentage returns 0 for zero amount."""
        household = Household.objects.create(name="Test Household")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Test", amount=Decimal("1.00")
        )
        # Directly test the logic
        item.amount = 0
        assert item.get_utilization_percentage() == 0

    def test_is_over_budget_true(self):
        """Test is_over_budget returns True when exceeded."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        category = Category.objects.create(household=household, name="Transport")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Transport", amount=Decimal("100.00"), category=category
        )

        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("-150.00"),
            description="Overspent on transport",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert item.is_over_budget() is True

    def test_is_over_budget_false(self):
        """Test is_over_budget returns False when under budget."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household, name="Checking", balance=Decimal("5000.00")
        )
        category = Category.objects.create(household=household, name="Utilities")
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("2000.00"),
            start_date=date(2025, 11, 1),
            end_date=date(2025, 11, 30),
        )
        item = BudgetItem.objects.create(
            budget=budget, name="Utilities", amount=Decimal("200.00"), category=category
        )

        Transaction.objects.create(
            account=account,
            category=category,
            amount=Decimal("-50.00"),
            description="Water bill",
            transaction_type="expense",
            status="completed",
            date=timezone.make_aware(timezone.datetime(2025, 11, 15)),
        )

        assert item.is_over_budget() is False
