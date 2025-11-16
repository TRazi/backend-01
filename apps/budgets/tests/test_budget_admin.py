"""
Tests for budgets admin interface.
"""

import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from budgets.admin import BudgetAdmin, BudgetItemAdmin, BudgetItemInline
from budgets.models import Budget, BudgetItem
from households.models import Household
from categories.models import Category
from accounts.models import Account
from transactions.models import Transaction

User = get_user_model()


@pytest.mark.django_db
class TestBudgetAdmin:
    """Test BudgetAdmin interface."""

    def test_list_display_fields(self):
        """Verify list_display contains expected fields."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert "name" in admin.list_display
        assert "household" in admin.list_display
        assert "total_amount" in admin.list_display
        assert "cycle_type" in admin.list_display
        assert "status" in admin.list_display
        assert "utilization" in admin.list_display

    def test_list_filter_fields(self):
        """Verify list_filter contains expected fields."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert "status" in admin.list_filter
        assert "cycle_type" in admin.list_filter
        assert "start_date" in admin.list_filter

    def test_search_fields(self):
        """Verify search_fields contains expected fields."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert "name" in admin.search_fields
        assert "household__name" in admin.search_fields
        assert "notes" in admin.search_fields

    def test_utilization_display_zero_percent(self):
        """Display shows 0.0% for budget with no spending."""
        household = Household.objects.create(name="Test Family")

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        admin = BudgetAdmin(Budget, AdminSite())
        result = admin.utilization(budget)

        assert "0.0%" in result

    def test_utilization_display_with_spending(self):
        """Display shows correct percentage with spending."""
        household = Household.objects.create(name="Test Family")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        # Create transaction within budget period
        Transaction.objects.create(
            account=account,
            budget=budget,
            category=category,
            transaction_type="expense",
            amount=Decimal("250.00"),
            description="Groceries",
            date=timezone.now(),
        )

        admin = BudgetAdmin(Budget, AdminSite())
        result = admin.utilization(budget)

        # Should show 25.0% (250/1000)
        assert "25.0%" in result

    def test_utilization_display_over_budget(self):
        """Display shows over 100% when over budget."""
        household = Household.objects.create(name="Test Family")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=2000
        )

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        # Create transaction over budget
        Transaction.objects.create(
            account=account,
            budget=budget,
            category=category,
            transaction_type="expense",
            amount=Decimal("1500.00"),
            description="Big expense",
            date=timezone.now(),
        )

        admin = BudgetAdmin(Budget, AdminSite())
        result = admin.utilization(budget)

        # Should show 150.0% (1500/1000)
        assert "150.0%" in result

    def test_utilization_short_description(self):
        """Verify short_description is set for utilization method."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert hasattr(admin.utilization, "short_description")
        assert admin.utilization.short_description == "Utilization"

    def test_get_queryset_uses_select_related(self):
        """Queryset uses select_related for optimization."""
        household = Household.objects.create(name="Test Family")

        Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        factory = RequestFactory()
        request = factory.get("/admin/budgets/budget/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = BudgetAdmin(Budget, AdminSite())
        queryset = admin.get_queryset(request)

        assert queryset.exists()
        budget = queryset.first()
        assert budget.household.name == "Test Family"

    def test_autocomplete_fields(self):
        """Verify autocomplete_fields are configured."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert "household" in admin.autocomplete_fields

    def test_date_hierarchy(self):
        """Verify date_hierarchy is set to start_date."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert admin.date_hierarchy == "start_date"

    def test_readonly_fields(self):
        """Verify readonly_fields contains timestamps."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_inlines_configured(self):
        """Verify BudgetItemInline is configured."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert len(admin.inlines) == 1
        assert admin.inlines[0] == BudgetItemInline

    def test_fieldsets_structure(self):
        """Verify fieldsets are properly organized."""
        admin = BudgetAdmin(Budget, AdminSite())

        assert len(admin.fieldsets) > 0

        # Check basic information section
        basic_info = admin.fieldsets[0]
        assert "Basic Information" in basic_info[0]
        assert "household" in basic_info[1]["fields"]
        assert "name" in basic_info[1]["fields"]


@pytest.mark.django_db
class TestBudgetItemAdmin:
    """Test BudgetItemAdmin interface."""

    def test_list_display_fields(self):
        """Verify list_display contains expected fields."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert "name" in admin.list_display
        assert "budget" in admin.list_display
        assert "amount" in admin.list_display
        assert "category" in admin.list_display
        assert "spent" in admin.list_display
        assert "remaining" in admin.list_display

    def test_list_filter_fields(self):
        """Verify list_filter contains expected fields."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert "budget__household" in admin.list_filter
        assert "category" in admin.list_filter
        assert "created_at" in admin.list_filter

    def test_search_fields(self):
        """Verify search_fields contains expected fields."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert "name" in admin.search_fields
        assert "budget__name" in admin.search_fields
        assert "category__name" in admin.search_fields

    def test_spent_display_zero(self):
        """Display shows $0.00 for item with no spending."""
        household = Household.objects.create(name="Test Family")

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        item = BudgetItem.objects.create(
            budget=budget, name="Groceries", amount=Decimal("300.00")
        )

        admin = BudgetItemAdmin(BudgetItem, AdminSite())
        result = admin.spent(item)

        assert "$0.00" in result

    def test_spent_display_with_category(self):
        """Display shows spent amount for item with category."""
        household = Household.objects.create(name="Test Family")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        item = BudgetItem.objects.create(
            budget=budget, category=category, name="Groceries", amount=Decimal("300.00")
        )

        # Create transaction in category
        Transaction.objects.create(
            account=account,
            budget=budget,
            category=category,
            transaction_type="expense",
            amount=Decimal("150.00"),
            description="Shopping",
            date=timezone.now(),
        )

        admin = BudgetItemAdmin(BudgetItem, AdminSite())
        result = admin.spent(item)

        assert "$150.00" in result

    def test_remaining_display(self):
        """Display shows remaining amount."""
        household = Household.objects.create(name="Test Family")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        item = BudgetItem.objects.create(
            budget=budget, category=category, name="Groceries", amount=Decimal("300.00")
        )

        # Create transaction
        Transaction.objects.create(
            account=account,
            budget=budget,
            category=category,
            transaction_type="expense",
            amount=Decimal("100.00"),
            description="Shopping",
            date=timezone.now(),
        )

        admin = BudgetItemAdmin(BudgetItem, AdminSite())
        result = admin.remaining(item)

        # Should show $200.00 (300 - 100)
        assert "$200.00" in result

    def test_spent_short_description(self):
        """Verify short_description is set for spent method."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert hasattr(admin.spent, "short_description")
        assert admin.spent.short_description == "Spent"

    def test_remaining_short_description(self):
        """Verify short_description is set for remaining method."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert hasattr(admin.remaining, "short_description")
        assert admin.remaining.short_description == "Remaining"

    def test_get_queryset_uses_select_related(self):
        """Queryset uses select_related for optimization."""
        household = Household.objects.create(name="Test Family")
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )

        budget = Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("1000.00"),
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
            cycle_type="monthly",
        )

        BudgetItem.objects.create(
            budget=budget, category=category, name="Groceries", amount=Decimal("300.00")
        )

        factory = RequestFactory()
        request = factory.get("/admin/budgets/budgetitem/")
        request.user = User.objects.create_user(
            email="admin@test.com", password="pass123", is_staff=True
        )

        admin = BudgetItemAdmin(BudgetItem, AdminSite())
        queryset = admin.get_queryset(request)

        assert queryset.exists()
        item = queryset.first()
        assert item.budget.name == "Monthly Budget"
        assert item.category.name == "Food"

    def test_autocomplete_fields(self):
        """Verify autocomplete_fields are configured."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert "budget" in admin.autocomplete_fields
        assert "category" in admin.autocomplete_fields

    def test_readonly_fields(self):
        """Verify readonly_fields contains timestamps."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_fieldsets_structure(self):
        """Verify fieldsets are properly organized."""
        admin = BudgetItemAdmin(BudgetItem, AdminSite())

        assert len(admin.fieldsets) > 0

        # Check budget item details section
        details = admin.fieldsets[0]
        assert "Budget Item Details" in details[0]
        assert "budget" in details[1]["fields"]
        assert "name" in details[1]["fields"]


@pytest.mark.django_db
class TestBudgetItemInline:
    """Test BudgetItemInline configuration."""

    def test_inline_model(self):
        """Verify inline is for BudgetItem model."""
        inline = BudgetItemInline(Budget, AdminSite())

        assert inline.model == BudgetItem

    def test_inline_extra(self):
        """Verify extra is set to 1."""
        inline = BudgetItemInline(Budget, AdminSite())

        assert inline.extra == 1

    def test_inline_fields(self):
        """Verify fields are configured."""
        inline = BudgetItemInline(Budget, AdminSite())

        assert "name" in inline.fields
        assert "amount" in inline.fields
        assert "category" in inline.fields
        assert "notes" in inline.fields

    def test_inline_autocomplete_fields(self):
        """Verify autocomplete_fields includes category."""
        inline = BudgetItemInline(Budget, AdminSite())

        assert "category" in inline.autocomplete_fields
