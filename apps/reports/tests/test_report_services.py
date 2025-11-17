"""
Tests for reports service functions.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone

from reports.services import (
    _get_household_for_user,
    generate_spending_report,
    export_household_snapshot,
    ReportAccessError,
)
from households.models import Household, Membership
from transactions.models import Transaction
from budgets.models import Budget
from goals.models import Goal
from accounts.models import Account
from categories.models import Category
from users.models import User


@pytest.mark.django_db
@pytest.mark.unit
def test_get_household_for_user_success():
    """Test getting household for valid member."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    result = _get_household_for_user(user=user, household_id=household.id)
    assert result == household


@pytest.mark.django_db
@pytest.mark.unit
def test_get_household_for_user_not_found():
    """Test getting non-existent household."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )

    with pytest.raises(ReportAccessError, match="Household not found"):
        _get_household_for_user(user=user, household_id=99999)


@pytest.mark.django_db
@pytest.mark.unit
def test_get_household_for_user_not_member():
    """Test getting household user is not member of."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    with pytest.raises(ReportAccessError, match="must be a member"):
        _get_household_for_user(user=user, household_id=household.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_generate_spending_report_basic():
    """Test basic spending report generation."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    account = Account.objects.create(
        name="Test Account",
        account_type="chq",
        balance=Decimal("1000.00"),
        household=household,
    )

    category = Category.objects.create(
        name="Groceries",
        category_type="ex",
        household=household,
    )

    # Create expense transactions
    now = timezone.now()
    Transaction.objects.create(
        account=account,
        amount=Decimal("-100.00"),
        description="Grocery shopping",
        transaction_type="expense",
        status="completed",
        date=now,
        category=category,
    )

    Transaction.objects.create(
        account=account,
        amount=Decimal("-50.00"),
        description="More groceries",
        transaction_type="expense",
        status="completed",
        date=now,
        category=category,
    )

    # Generate report
    from_date = now - timedelta(days=1)
    to_date = now + timedelta(days=1)

    result = generate_spending_report(
        user=user,
        household_id=household.id,
        from_date=from_date,
        to_date=to_date,
    )

    assert result["summary"]["total_spent"] == "150.00"
    assert result["summary"]["category_count"] == 1
    assert len(result["by_category"]) == 1
    assert result["by_category"][0]["category_name"] == "Groceries"
    assert result["by_category"][0]["spent"] == "150.00"
    assert result["by_category"][0]["percentage_of_total"] == pytest.approx(100.0)


@pytest.mark.django_db
@pytest.mark.unit
def test_generate_spending_report_with_category_filter():
    """Test spending report with category filter."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    account = Account.objects.create(
        name="Test Account",
        account_type="chq",
        balance=Decimal("1000.00"),
        household=household,
    )

    category1 = Category.objects.create(
        name="Groceries",
        category_type="ex",
        household=household,
    )

    category2 = Category.objects.create(
        name="Entertainment",
        category_type="ex",
        household=household,
    )

    now = timezone.now()

    Transaction.objects.create(
        account=account,
        amount=Decimal("-100.00"),
        description="Groceries",
        transaction_type="expense",
        status="completed",
        date=now,
        category=category1,
    )

    Transaction.objects.create(
        account=account,
        amount=Decimal("-50.00"),
        description="Movie",
        transaction_type="expense",
        status="completed",
        date=now,
        category=category2,
    )

    # Filter by category1 only
    from_date = now - timedelta(days=1)
    to_date = now + timedelta(days=1)

    result = generate_spending_report(
        user=user,
        household_id=household.id,
        from_date=from_date,
        to_date=to_date,
        category_id=category1.id,
    )

    assert result["summary"]["total_spent"] == "100.00"
    assert result["summary"]["category_count"] == 1
    assert result["by_category"][0]["category_name"] == "Groceries"


@pytest.mark.django_db
@pytest.mark.unit
def test_generate_spending_report_multiple_categories():
    """Test spending report with multiple categories showing percentages."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    account = Account.objects.create(
        name="Test Account",
        account_type="chq",
        balance=Decimal("1000.00"),
        household=household,
    )

    cat_groceries = Category.objects.create(
        name="Groceries",
        category_type="ex",
        household=household,
    )

    cat_entertainment = Category.objects.create(
        name="Entertainment",
        category_type="ex",
        household=household,
    )

    now = timezone.now()

    # 75% groceries
    Transaction.objects.create(
        account=account,
        amount=Decimal("-75.00"),
        description="Groceries",
        transaction_type="expense",
        status="completed",
        date=now,
        category=cat_groceries,
    )

    # 25% entertainment
    Transaction.objects.create(
        account=account,
        amount=Decimal("-25.00"),
        description="Movie",
        transaction_type="expense",
        status="completed",
        date=now,
        category=cat_entertainment,
    )

    from_date = now - timedelta(days=1)
    to_date = now + timedelta(days=1)

    result = generate_spending_report(
        user=user,
        household_id=household.id,
        from_date=from_date,
        to_date=to_date,
    )

    assert result["summary"]["total_spent"] == "100.00"
    assert result["summary"]["category_count"] == 2

    # Check percentages
    by_cat = {cat["category_name"]: cat for cat in result["by_category"]}
    assert abs(by_cat["Entertainment"]["percentage_of_total"] - 25.0) < 0.01
    assert abs(by_cat["Groceries"]["percentage_of_total"] - 75.0) < 0.01


@pytest.mark.django_db
@pytest.mark.unit
def test_generate_spending_report_excludes_non_expenses():
    """Test that spending report only includes expense transactions."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    account = Account.objects.create(
        name="Test Account",
        account_type="chq",
        balance=Decimal("1000.00"),
        household=household,
    )

    category = Category.objects.create(
        name="Test Category",
        category_type="ex",
        household=household,
    )

    now = timezone.now()

    # Expense - should be included
    Transaction.objects.create(
        account=account,
        amount=Decimal("-100.00"),
        description="Expense",
        transaction_type="expense",
        status="completed",
        date=now,
        category=category,
    )

    # Income - should be excluded
    Transaction.objects.create(
        account=account,
        amount=Decimal("500.00"),
        description="Income",
        transaction_type="income",
        status="completed",
        date=now,
        category=category,
    )

    from_date = now - timedelta(days=1)
    to_date = now + timedelta(days=1)

    result = generate_spending_report(
        user=user,
        household_id=household.id,
        from_date=from_date,
        to_date=to_date,
    )

    # Only expense should be counted
    assert result["summary"]["total_spent"] == "100.00"


@pytest.mark.django_db
@pytest.mark.unit
def test_export_household_snapshot():
    """Test household snapshot export."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    # Create test data
    Account.objects.create(
        name="Checking",
        account_type="chq",
        balance=Decimal("1000.00"),
        household=household,
    )

    now = timezone.now()
    Budget.objects.create(
        name="Monthly Budget",
        household=household,
        total_amount=Decimal("500.00"),
        start_date=now.date(),
        end_date=(now + timedelta(days=30)).date(),
    )

    Goal.objects.create(
        name="Vacation Fund",
        household=household,
        target_amount=Decimal("2000.00"),
        current_amount=Decimal("500.00"),
        due_date=(now + timedelta(days=180)).date(),
    )

    Category.objects.create(
        name="Groceries",
        category_type="ex",
        household=household,
    )

    result = export_household_snapshot(
        user=user,
        household_id=household.id,
    )

    # Check metadata
    assert result["metadata"]["household_id"] == household.id
    assert result["metadata"]["household_name"] == "Test Household"

    # Check accounts
    assert len(result["accounts"]) == 1
    assert result["accounts"][0]["name"] == "Checking"
    assert result["accounts"][0]["balance"] == "1000.00"

    # Check budgets
    assert len(result["budgets"]) == 1
    assert result["budgets"][0]["name"] == "Monthly Budget"
    assert result["budgets"][0]["total_amount"] == "500.00"

    # Check goals
    assert len(result["goals"]) == 1
    assert result["goals"][0]["name"] == "Vacation Fund"
    assert result["goals"][0]["target_amount"] == "2000.00"

    # Check categories
    assert len(result["categories"]) == 1
    assert result["categories"][0]["name"] == "Groceries"


@pytest.mark.django_db
@pytest.mark.unit
def test_export_household_snapshot_excludes_deleted_categories():
    """Test that snapshot excludes deleted categories."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    # Active category
    Category.objects.create(
        name="Active",
        category_type="ex",
        household=household,
        is_deleted=False,
    )

    # Deleted category
    Category.objects.create(
        name="Deleted",
        category_type="ex",
        household=household,
        is_deleted=True,
    )

    result = export_household_snapshot(
        user=user,
        household_id=household.id,
    )

    # Only active category should be included
    assert len(result["categories"]) == 1
    assert result["categories"][0]["name"] == "Active"
