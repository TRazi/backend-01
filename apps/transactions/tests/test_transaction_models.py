"""
Tests for Transaction model validation and methods.
"""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.households.models import Household
from apps.accounts.models import Account
from apps.transactions.models import Transaction, TransactionTag
from apps.categories.models import Category
from apps.budgets.models import Budget
from apps.goals.models import Goal


@pytest.mark.django_db
class TestTransactionValidation:
    """Test Transaction model validation."""

    def test_clean_validates_zero_amount(self):
        """Transaction with zero amount is invalid."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction(
            account=account,
            transaction_type="expense",
            amount=Decimal("0.00"),
            description="Invalid",
            date=timezone.now(),
        )

        with pytest.raises(ValidationError, match="amount cannot be zero"):
            transaction.clean()

    def test_clean_validates_expense_positive_amount(self):
        """Expense transaction with positive amount is invalid."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction(
            account=account,
            transaction_type="expense",
            amount=Decimal("50.00"),
            description="Invalid expense",
            date=timezone.now(),
        )

        with pytest.raises(
            ValidationError, match="Expense transactions must have negative amounts"
        ):
            transaction.clean()

    def test_clean_validates_income_negative_amount(self):
        """Income transaction with negative amount is invalid."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction(
            account=account,
            transaction_type="income",
            amount=Decimal("-50.00"),
            description="Invalid income",
            date=timezone.now(),
        )

        with pytest.raises(
            ValidationError, match="Income transactions must have positive amounts"
        ):
            transaction.clean()

    def test_clean_validates_budget_household_mismatch(self):
        """Budget must belong to same household as account."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        account = Account.objects.create(
            household=household1, name="Checking", account_type="checking", balance=0
        )
        budget = Budget.objects.create(
            household=household2,
            name="Budget",
            total_amount=Decimal("1000.00"),
            cycle_type="monthly",
            start_date=timezone.now().date(),
            end_date=(timezone.now() + timedelta(days=30)).date(),
        )

        transaction = Transaction(
            account=account,
            budget=budget,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
        )

        with pytest.raises(
            ValidationError, match="Budget must belong to the same household"
        ):
            transaction.clean()

    def test_clean_validates_goal_household_mismatch(self):
        """Goal must belong to same household as account."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        account = Account.objects.create(
            household=household1, name="Checking", account_type="checking", balance=0
        )
        goal = Goal.objects.create(
            household=household2,
            name="Goal",
            target_amount=Decimal("5000.00"),
            due_date=(timezone.now() + timedelta(days=365)).date(),
        )

        transaction = Transaction(
            account=account,
            goal=goal,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
        )

        with pytest.raises(
            ValidationError, match="Goal must belong to the same household"
        ):
            transaction.clean()

    def test_clean_validates_transfer_requires_linked_transaction(self):
        """Transfer transaction requires linked_transaction."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction(
            account=account,
            transaction_type="transfer",
            amount=Decimal("-100.00"),
            description="Transfer",
            date=timezone.now(),
        )

        with pytest.raises(
            ValidationError,
            match="Transfer transactions must have a linked_transaction",
        ):
            transaction.clean()

    def test_valid_expense_transaction(self):
        """Valid expense transaction passes validation."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        transaction = Transaction(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Groceries",
            date=timezone.now(),
        )

        # Should not raise
        transaction.clean()

    def test_valid_income_transaction(self):
        """Valid income transaction passes validation."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        transaction = Transaction(
            account=account,
            transaction_type="income",
            amount=Decimal("500.00"),
            description="Salary",
            date=timezone.now(),
        )

        # Should not raise
        transaction.clean()


@pytest.mark.django_db
class TestTransactionProperties:
    """Test Transaction model properties."""

    def test_is_pending_property(self):
        """is_pending returns True for pending transactions."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
            status="pending",
        )

        assert transaction.is_pending is True

    def test_is_pending_property_false(self):
        """is_pending returns False for non-pending transactions."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
            status="completed",
        )

        assert transaction.is_pending is False

    def test_is_completed_property(self):
        """is_completed returns True for completed transactions."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
            status="completed",
        )

        assert transaction.is_completed is True

    def test_is_completed_property_false(self):
        """is_completed returns False for non-completed transactions."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
            status="pending",
        )

        assert transaction.is_completed is False

    def test_str_method(self):
        """__str__ returns formatted string."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        date = timezone.now()
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-75.50"),
            description="Groceries",
            date=date,
        )

        expected = f"Groceries - $-75.50 ({date.strftime('%Y-%m-%d')})"
        assert str(transaction) == expected


@pytest.mark.django_db
class TestTransactionTagModel:
    """Test TransactionTag model."""

    def test_create_transaction_tag(self):
        """Can create transaction tag."""
        household = Household.objects.create(name="Test Family")
        tag = TransactionTag.objects.create(
            household=household,
            name="groceries",
            color="#FF5733",
            description="Grocery shopping",
        )

        assert tag.name == "groceries"
        assert tag.color == "#FF5733"

    def test_transaction_tag_unique_per_household(self):
        """Tag names are unique per household."""
        household = Household.objects.create(name="Test Family")
        TransactionTag.objects.create(household=household, name="groceries")

        # Second tag with same name should fail
        with pytest.raises(Exception):  # IntegrityError
            TransactionTag.objects.create(household=household, name="groceries")

    def test_transaction_tag_same_name_different_household(self):
        """Same tag name can exist in different households."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        tag1 = TransactionTag.objects.create(household=household1, name="groceries")
        tag2 = TransactionTag.objects.create(household=household2, name="groceries")

        assert tag1.id != tag2.id
        assert tag1.name == tag2.name

    def test_transaction_tag_str_method(self):
        """__str__ returns formatted string."""
        household = Household.objects.create(name="Test Family")
        tag = TransactionTag.objects.create(household=household, name="groceries")

        assert str(tag) == "groceries (Test Family)"

    def test_transaction_tag_default_color(self):
        """Tag has default color."""
        household = Household.objects.create(name="Test Family")
        tag = TransactionTag.objects.create(household=household, name="test")

        assert tag.color == "#6B7280"


@pytest.mark.django_db
class TestTransactionRelationships:
    """Test Transaction model relationships."""

    def test_transaction_with_tags(self):
        """Transaction can have multiple tags."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Test",
            date=timezone.now(),
        )

        tag1 = TransactionTag.objects.create(household=household, name="groceries")
        tag2 = TransactionTag.objects.create(household=household, name="essential")

        transaction.tags.add(tag1, tag2)

        assert transaction.tags.count() == 2

    def test_linked_transaction_relationship(self):
        """Can link two transactions for transfers."""
        household = Household.objects.create(name="Test Family")
        account1 = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )
        account2 = Account.objects.create(
            household=household, name="Savings", account_type="savings", balance=500
        )

        tx1 = Transaction.objects.create(
            account=account1,
            transaction_type="expense",
            amount=Decimal("-100.00"),
            description="Transfer out",
            date=timezone.now(),
        )

        tx2 = Transaction.objects.create(
            account=account2,
            transaction_type="income",
            amount=Decimal("100.00"),
            description="Transfer in",
            date=timezone.now(),
        )

        tx1.linked_transaction = tx2
        tx1.save()

        assert tx1.linked_transaction == tx2
