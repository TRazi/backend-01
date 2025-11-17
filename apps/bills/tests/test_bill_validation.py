"""
Tests for Bill model validation methods.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError

from apps.bills.models import Bill
from apps.households.models import Household
from apps.categories.models import Category
from apps.accounts.models import Account


@pytest.mark.django_db
@pytest.mark.unit
class TestBillValidation:
    """Test Bill model validation in clean() method."""

    def test_clean_validates_positive_amount(self):
        """Test clean raises error for non-positive amount."""
        household = Household.objects.create(name="Test Household")
        bill = Bill(
            household=household,
            name="Invalid Bill",
            amount=Decimal("-50.00"),
            due_date=date.today() + timedelta(days=7),
        )
        with pytest.raises(ValidationError, match="amount must be greater than zero"):
            bill.clean()

    def test_clean_validates_zero_amount(self):
        """Test clean raises error for zero amount."""
        household = Household.objects.create(name="Test Household")
        bill = Bill(
            household=household,
            name="Zero Bill",
            amount=Decimal("0.00"),
            due_date=date.today() + timedelta(days=7),
        )
        with pytest.raises(ValidationError, match="amount must be greater than zero"):
            bill.clean()

    def test_clean_validates_paid_date_not_before_due_date(self):
        """Test clean raises error when paid_date is before due_date."""
        household = Household.objects.create(name="Test Household")
        bill = Bill(
            household=household,
            name="Invalid Paid Bill",
            amount=Decimal("100.00"),
            due_date=date(2025, 12, 31),
            paid_date=date(2025, 12, 1),  # Before due_date
        )
        with pytest.raises(
            ValidationError, match="paid_date cannot be before due_date"
        ):
            bill.clean()

    def test_clean_validates_category_household(self):
        """Test clean validates category belongs to same household."""
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        category = Category.objects.create(household=household2, name="Utilities")

        bill = Bill(
            household=household1,
            name="Cross-household Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=7),
            category=category,
        )
        with pytest.raises(
            ValidationError, match="Category must belong to the same household"
        ):
            bill.clean()

    def test_clean_validates_account_household(self):
        """Test clean validates account belongs to same household."""
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        account = Account.objects.create(
            household=household2,
            name="Other Account",
            balance=Decimal("1000.00"),
        )

        bill = Bill(
            household=household1,
            name="Cross-household Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=7),
            account=account,
        )
        with pytest.raises(
            ValidationError, match="Account must belong to the same household"
        ):
            bill.clean()

    def test_clean_validates_paid_status_requires_paid_date(self):
        """Test clean raises error when status is paid but no paid_date."""
        household = Household.objects.create(name="Test Household")
        bill = Bill(
            household=household,
            name="Paid Bill Without Date",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=7),
            status="paid",
            paid_date=None,
        )
        with pytest.raises(
            ValidationError, match="paid_date must be set when status is 'paid'"
        ):
            bill.clean()

    def test_clean_passes_for_valid_bill(self):
        """Test clean passes for valid bill data."""
        household = Household.objects.create(name="Test Household")
        bill = Bill(
            household=household,
            name="Valid Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=7),
            status="pending",
        )
        # Should not raise any exception
        bill.clean()

    def test_clean_passes_for_valid_paid_bill(self):
        """Test clean passes for valid paid bill."""
        household = Household.objects.create(name="Test Household")
        due = date.today()
        paid = due + timedelta(days=1)

        bill = Bill(
            household=household,
            name="Valid Paid Bill",
            amount=Decimal("100.00"),
            due_date=due,
            paid_date=paid,
            status="paid",
        )
        # Should not raise any exception
        bill.clean()
