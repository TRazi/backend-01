"""
Tests for bills app models.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.bills.models import Bill
from apps.households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
class TestBillModel:
    """Test Bill model methods and properties."""

    def test_str_method(self):
        """Test __str__ method returns bill name with amount and due date."""
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="Electric Bill",
            amount=150.00,
            due_date=date(2025, 12, 1),
        )
        assert str(bill) == "Electric Bill - $150.0 (Due: 2025-12-01)"

    def test_is_overdue_property_true(self):
        """Test is_overdue returns True for past due bills."""
        household = Household.objects.create(name="Test Household")
        past_date = date.today() - timedelta(days=5)
        bill = Bill.objects.create(
            household=household,
            name="Overdue Bill",
            amount=100.00,
            due_date=past_date,
            status="pending",
        )
        assert bill.is_overdue is True

    def test_is_overdue_property_false_for_future(self):
        """Test is_overdue returns False for future bills."""
        household = Household.objects.create(name="Test Household")
        future_date = date.today() + timedelta(days=5)
        bill = Bill.objects.create(
            household=household,
            name="Future Bill",
            amount=100.00,
            due_date=future_date,
            status="pending",
        )
        assert bill.is_overdue is False

    def test_is_overdue_property_false_for_paid(self):
        """Test is_overdue returns False for paid bills."""
        household = Household.objects.create(name="Test Household")
        past_date = date.today() - timedelta(days=5)
        bill = Bill.objects.create(
            household=household,
            name="Paid Bill",
            amount=100.00,
            due_date=past_date,
            status="paid",
        )
        assert bill.is_overdue is False

    def test_is_upcoming_property_true(self):
        """Test is_upcoming returns True for bills due within 7 days."""
        household = Household.objects.create(name="Test Household")
        upcoming_date = date.today() + timedelta(days=3)
        bill = Bill.objects.create(
            household=household,
            name="Upcoming Bill",
            amount=100.00,
            due_date=upcoming_date,
        )
        assert bill.is_upcoming is True

    def test_is_upcoming_property_false(self):
        """Test is_upcoming returns False for bills beyond 7 days."""
        household = Household.objects.create(name="Test Household")
        far_future_date = date.today() + timedelta(days=10)
        bill = Bill.objects.create(
            household=household,
            name="Far Future Bill",
            amount=100.00,
            due_date=far_future_date,
        )
        assert bill.is_upcoming is False

    def test_days_until_due_property_positive(self):
        """Test days_until_due returns positive number for future bills."""
        household = Household.objects.create(name="Test Household")
        future_date = date.today() + timedelta(days=5)
        bill = Bill.objects.create(
            household=household, name="Future Bill", amount=100.00, due_date=future_date
        )
        assert bill.days_until_due in [5, 6]

    def test_days_until_due_property_negative(self):
        """Test days_until_due returns negative number for overdue bills."""
        household = Household.objects.create(name="Test Household")
        past_date = date.today() - timedelta(days=3)
        bill = Bill.objects.create(
            household=household, name="Overdue Bill", amount=100.00, due_date=past_date
        )
        assert bill.days_until_due in [-3, -2]

    def test_should_send_reminder_property_true(self):
        """Test should_send_reminder returns True when reminder needed."""
        household = Household.objects.create(name="Test Household")
        upcoming_date = date.today() + timedelta(days=2)
        bill = Bill.objects.create(
            household=household,
            name="Reminder Bill",
            amount=100.00,
            due_date=upcoming_date,
            status="pending",
        )
        assert bill.should_send_reminder is True

    def test_should_send_reminder_property_false_too_early(self):
        """Test should_send_reminder returns False when too early."""
        household = Household.objects.create(name="Test Household")
        future_date = date.today() + timedelta(days=10)
        bill = Bill.objects.create(
            household=household,
            name="Future Bill",
            amount=100.00,
            due_date=future_date,
            status="pending",
        )
        assert bill.should_send_reminder is False

    def test_should_send_reminder_property_false_paid(self):
        """Test should_send_reminder returns False for paid bills."""
        household = Household.objects.create(name="Test Household")
        upcoming_date = date.today() + timedelta(days=2)
        bill = Bill.objects.create(
            household=household,
            name="Paid Bill",
            amount=100.00,
            due_date=upcoming_date,
            status="paid",
        )
        assert bill.should_send_reminder is False

    def test_calculate_next_due_date_monthly(self):
        """Test calculate_next_due_date for monthly recurrence."""
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="Monthly Bill",
            amount=100.00,
            due_date=date(2025, 11, 15),
            frequency="monthly",
            is_recurring=True,
        )
        next_date = bill.calculate_next_due_date()
        assert next_date == date(2025, 12, 15)

    def test_calculate_next_due_date_weekly(self):
        """Test calculate_next_due_date for weekly recurrence."""
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="Weekly Bill",
            amount=50.00,
            due_date=date(2025, 11, 14),
            frequency="weekly",
            is_recurring=True,
        )
        next_date = bill.calculate_next_due_date()
        assert next_date == date(2025, 11, 21)

    def test_calculate_next_due_date_yearly(self):
        """Test calculate_next_due_date for yearly recurrence."""
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="Yearly Bill",
            amount=1000.00,
            due_date=date(2025, 11, 14),
            frequency="yearly",
            is_recurring=True,
        )
        next_date = bill.calculate_next_due_date()
        assert next_date == date(2026, 11, 14)

    def test_calculate_next_due_date_none_for_one_time(self):
        """Test calculate_next_due_date returns None for one-time bills."""
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="One Time Bill",
            amount=200.00,
            due_date=date(2025, 11, 14),
            frequency="monthly",
            is_recurring=False,
        )
        next_date = bill.calculate_next_due_date()
        assert next_date is None
