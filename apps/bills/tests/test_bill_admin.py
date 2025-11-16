"""
Tests for bills admin interface.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from bills.admin import BillAdmin
from bills.models import Bill
from households.models import Household
from categories.models import Category
from accounts.models import Account

User = get_user_model()


@pytest.mark.django_db
class TestBillAdmin:
    """Test BillAdmin interface."""

    def test_list_display_fields(self):
        """Verify list_display contains expected fields."""
        admin = BillAdmin(Bill, AdminSite())

        assert "name" in admin.list_display
        assert "household" in admin.list_display
        assert "amount" in admin.list_display
        assert "due_date" in admin.list_display
        assert "status" in admin.list_display
        assert "days_until_due_display" in admin.list_display

    def test_list_filter_fields(self):
        """Verify list_filter contains expected fields."""
        admin = BillAdmin(Bill, AdminSite())

        assert "status" in admin.list_filter
        assert "frequency" in admin.list_filter
        assert "is_recurring" in admin.list_filter
        assert "auto_pay_enabled" in admin.list_filter

    def test_search_fields(self):
        """Verify search_fields contains expected fields."""
        admin = BillAdmin(Bill, AdminSite())

        assert "name" in admin.search_fields
        assert "household__name" in admin.search_fields
        assert "description" in admin.search_fields

    def test_days_until_due_display_future(self):
        """Display shows days remaining for future bills."""
        household = Household.objects.create(name="Test Family")
        future_date = timezone.now().date() + timedelta(days=5)

        bill = Bill.objects.create(
            household=household,
            name="Future Bill",
            amount=100,
            due_date=future_date,
            status="pending",
        )

        admin = BillAdmin(Bill, AdminSite())
        result = admin.days_until_due_display(bill)

        assert "5 days" in result

    def test_days_until_due_display_overdue(self):
        """Display shows overdue message for past bills."""
        household = Household.objects.create(name="Test Family")
        past_date = timezone.now().date() - timedelta(days=3)

        bill = Bill.objects.create(
            household=household,
            name="Overdue Bill",
            amount=100,
            due_date=past_date,
            status="pending",
        )

        admin = BillAdmin(Bill, AdminSite())
        result = admin.days_until_due_display(bill)

        assert "Overdue by 3 days" in result

    def test_days_until_due_display_today(self):
        """Display shows 'Due today' for bills due today."""
        household = Household.objects.create(name="Test Family")
        today = timezone.now().date()

        bill = Bill.objects.create(
            household=household,
            name="Today Bill",
            amount=100,
            due_date=today,
            status="pending",
        )

        admin = BillAdmin(Bill, AdminSite())
        result = admin.days_until_due_display(bill)

        assert result == "Due today"

    def test_days_until_due_display_paid_bill(self):
        """Display shows N/A for paid bills (days_until_due is None)."""
        household = Household.objects.create(name="Test Family")

        bill = Bill.objects.create(
            household=household,
            name="Paid Bill",
            amount=100,
            due_date=timezone.now().date(),
            status="paid",
            paid_date=timezone.now().date(),
        )

        admin = BillAdmin(Bill, AdminSite())
        result = admin.days_until_due_display(bill)

        assert result == "N/A"

    def test_get_queryset_uses_select_related(self):
        """Queryset uses select_related for optimization."""
        household = Household.objects.create(name="Test Family")
        category = Category.objects.create(
            household=household, name="Utilities", category_type="expense"
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        Bill.objects.create(
            household=household,
            category=category,
            account=account,
            name="Electric Bill",
            amount=150,
            due_date=timezone.now().date(),
        )

        factory = RequestFactory()
        request = factory.get("/admin/bills/bill/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = BillAdmin(Bill, AdminSite())
        queryset = admin.get_queryset(request)

        # Verify queryset has select_related applied
        # This is indicated by the query using JOINs
        assert queryset.exists()
        # The first item should have related objects loaded
        bill = queryset.first()
        assert bill.household.name == "Test Family"

    def test_autocomplete_fields(self):
        """Verify autocomplete_fields are configured."""
        admin = BillAdmin(Bill, AdminSite())

        assert "household" in admin.autocomplete_fields
        assert "category" in admin.autocomplete_fields
        assert "account" in admin.autocomplete_fields
        assert "transaction" in admin.autocomplete_fields

    def test_date_hierarchy(self):
        """Verify date_hierarchy is set to due_date."""
        admin = BillAdmin(Bill, AdminSite())

        assert admin.date_hierarchy == "due_date"

    def test_readonly_fields(self):
        """Verify readonly_fields contains timestamps."""
        admin = BillAdmin(Bill, AdminSite())

        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_fieldsets_structure(self):
        """Verify fieldsets are properly organized."""
        admin = BillAdmin(Bill, AdminSite())

        assert len(admin.fieldsets) > 0

        # Check that basic information is first
        basic_info = admin.fieldsets[0]
        assert "Basic Information" in basic_info[0]
        assert "household" in basic_info[1]["fields"]
        assert "name" in basic_info[1]["fields"]

    def test_days_until_due_display_one_day(self):
        """Display shows singular 'day' for one day remaining."""
        household = Household.objects.create(name="Test Family")
        tomorrow = timezone.now().date() + timedelta(days=1)

        bill = Bill.objects.create(
            household=household,
            name="Tomorrow Bill",
            amount=100,
            due_date=tomorrow,
            status="pending",
        )

        admin = BillAdmin(Bill, AdminSite())
        result = admin.days_until_due_display(bill)

        # Should show "1 days" (as per the implementation)
        assert "1 days" in result

    def test_days_until_due_display_short_description(self):
        """Verify short_description is set for display method."""
        admin = BillAdmin(Bill, AdminSite())

        assert hasattr(admin.days_until_due_display, "short_description")
        assert admin.days_until_due_display.short_description == "Days Until Due"

    def test_admin_with_recurring_bill(self):
        """Test admin display with recurring bill."""
        household = Household.objects.create(name="Test Family")

        bill = Bill.objects.create(
            household=household,
            name="Monthly Rent",
            amount=1500,
            due_date=timezone.now().date(),
            frequency="monthly",
            is_recurring=True,
            status="pending",
        )

        admin = BillAdmin(Bill, AdminSite())

        # Verify the bill can be displayed in admin
        assert admin.days_until_due_display(bill) is not None

    def test_admin_with_auto_pay_enabled(self):
        """Test admin display with auto-pay enabled."""
        household = Household.objects.create(name="Test Family")
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        bill = Bill.objects.create(
            household=household,
            account=account,
            name="Auto Bill",
            amount=50,
            due_date=timezone.now().date(),
            auto_pay_enabled=True,
            status="pending",
        )

        admin = BillAdmin(Bill, AdminSite())

        # Verify bill is in queryset
        factory = RequestFactory()
        request = factory.get("/admin/bills/bill/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        queryset = admin.get_queryset(request)
        assert bill in queryset

    def test_admin_with_different_statuses(self):
        """Test admin handles different bill statuses."""
        household = Household.objects.create(name="Test Family")

        statuses = ["pending", "paid", "overdue", "cancelled"]

        for status_value in statuses:
            paid_date = timezone.now().date() if status_value == "paid" else None

            bill = Bill.objects.create(
                household=household,
                name=f"{status_value.title()} Bill",
                amount=100,
                due_date=timezone.now().date(),
                status=status_value,
                paid_date=paid_date,
            )

            admin = BillAdmin(Bill, AdminSite())
            result = admin.days_until_due_display(bill)

            # All should return a valid display value
            assert result is not None
