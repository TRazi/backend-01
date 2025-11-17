"""Additional tests for Bill model properties to reach 85% coverage."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.bills.models import Bill
from apps.households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
class TestBillPropertiesEdgeCases:
    """Test edge cases for Bill model properties."""

    def test_is_upcoming_property_true(self):
        """Test is_upcoming returns True for bills due within 7 days."""
        household = Household.objects.create(name="Test Household")
        upcoming_bill = Bill.objects.create(
            household=household,
            name="Upcoming Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=5),
            status="pending",
        )
        assert upcoming_bill.is_upcoming is True

    def test_is_upcoming_property_false_too_far(self):
        """Test is_upcoming returns False for bills due beyond 7 days."""
        household = Household.objects.create(name="Test Household")
        future_bill = Bill.objects.create(
            household=household,
            name="Future Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=10),
            status="pending",
        )
        assert future_bill.is_upcoming is False

    def test_is_upcoming_property_false_for_paid_bills(self):
        """Test is_upcoming returns False for paid bills."""
        household = Household.objects.create(name="Test Household")
        paid_bill = Bill.objects.create(
            household=household,
            name="Paid Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=3),
            status="paid",
        )
        assert paid_bill.is_upcoming is False

    def test_days_until_due_property_none_for_paid_bills(self):
        """Test days_until_due returns None for paid bills."""
        household = Household.objects.create(name="Test Household")
        paid_bill = Bill.objects.create(
            household=household,
            name="Paid Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=5),
            status="paid",
        )
        assert paid_bill.days_until_due is None

    def test_days_until_due_property_none_for_cancelled_bills(self):
        """Test days_until_due returns None for cancelled bills."""
        household = Household.objects.create(name="Test Household")
        cancelled_bill = Bill.objects.create(
            household=household,
            name="Cancelled Bill",
            amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=5),
            status="cancelled",
        )
        assert cancelled_bill.days_until_due is None
