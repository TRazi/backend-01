"""
Tests for privacy service functions.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from django.utils import timezone

from privacy.services import (
    _get_household_for_user,
    _serialize_transaction,
    _serialize_budget,
    _serialize_goal,
    HouseholdAccessError,
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

    with pytest.raises(HouseholdAccessError, match="Household not found"):
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

    with pytest.raises(HouseholdAccessError, match="must be a member"):
        _get_household_for_user(user=user, household_id=household.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_get_household_for_user_ended_membership():
    """Test getting household with ended membership."""
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
        ended_at=timezone.now(),
    )

    with pytest.raises(HouseholdAccessError, match="must be a member"):
        _get_household_for_user(user=user, household_id=household.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_serialize_transaction():
    """Test transaction serialization."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
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

    transaction = Transaction.objects.create(
        account=account,
        amount=Decimal("100.50"),
        description="Test transaction",
        transaction_type="expense",
        date=timezone.now(),
        category=category,
    )

    result = _serialize_transaction(transaction)

    assert result["id"] == transaction.id
    assert result["amount"] == "100.50"
    assert result["description"] == "Test transaction"
    assert result["transaction_type"] == "expense"
    assert result["account"] == account.id
    assert result["category"] == category.id
    assert "date" in result
    assert "created_at" in result


@pytest.mark.django_db
@pytest.mark.unit
def test_serialize_budget():
    """Test budget serialization."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    from datetime import timedelta

    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=30)

    budget = Budget.objects.create(
        name="Test Budget",
        household=household,
        total_amount=Decimal("500.00"),
        start_date=start_date,
        end_date=end_date,
    )

    result = _serialize_budget(budget)

    assert result["id"] == budget.id
    assert result["name"] == "Test Budget"
    assert result["total_amount"] == "500.00"
    assert "start_date" in result
    assert "created_at" in result


@pytest.mark.django_db
@pytest.mark.unit
def test_serialize_goal():
    """Test goal serialization."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    goal = Goal.objects.create(
        name="Test Goal",
        household=household,
        target_amount=Decimal("1000.00"),
        current_amount=Decimal("250.00"),
        goal_type="savings",
        due_date=timezone.now().date(),
    )

    result = _serialize_goal(goal)

    assert result["id"] == goal.id
    assert result["name"] == "Test Goal"
    assert result["target_amount"] == "1000.00"
    assert result["current_amount"] == "250.00"
    assert result["status"] == "active"  # default status


# --- Tests for export_user_data, request_data_deletion, get_data_deletion_status ---


@pytest.mark.django_db
@pytest.mark.unit
def test_export_user_data_success():
    """Test full data export for a household member."""
    from privacy.services import export_user_data

    user = User.objects.create_user(
        email="export@example.com",
        password="testpass123",
        first_name="John",
        last_name="Doe",
    )
    household = Household.objects.create(
        name="Export Household",
        household_type="fam",
        budget_cycle="m",
    )
    membership = Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )

    Account.objects.create(
        name="Test Account",
        account_type="chq",
        balance=Decimal("1000.00"),
        household=household,
    )

    result = export_user_data(user=user, household_id=household.id)

    # Check metadata
    assert result["metadata"]["household_id"] == household.id
    assert result["metadata"]["household_name"] == "Export Household"
    assert result["metadata"]["user_id"] == user.id
    assert "exported_at" in result["metadata"]

    # Check user data
    assert result["user"]["email"] == "export@example.com"
    assert result["user"]["first_name"] == "John"
    assert result["user"]["last_name"] == "Doe"

    # Check membership
    assert result["membership"]["id"] == membership.id
    assert result["membership"]["role"] == "admin"

    # Check collections
    assert "accounts" in result
    assert "budgets" in result
    assert "goals" in result
    assert "transactions" in result
    assert len(result["accounts"]) == 1


@pytest.mark.django_db
@pytest.mark.unit
def test_export_user_data_includes_transactions():
    """Test exported data includes transactions."""
    from privacy.services import export_user_data

    user = User.objects.create_user(
        email="export@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Export Household",
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

    transaction = Transaction.objects.create(
        account=account,
        amount=Decimal("50.00"),
        description="Test transaction",
        transaction_type="expense",
        date=timezone.now(),
        category=category,
    )

    result = export_user_data(user=user, household_id=household.id)

    assert len(result["transactions"]) == 1
    txn_data = result["transactions"][0]
    assert txn_data["id"] == transaction.id
    assert txn_data["amount"] == "50.00"
    assert txn_data["description"] == "Test transaction"


@pytest.mark.django_db
@pytest.mark.unit
def test_export_user_data_non_member_denied():
    """Test export fails for non-household member."""
    from privacy.services import export_user_data

    user = User.objects.create_user(
        email="export@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Other Household",
        household_type="fam",
        budget_cycle="m",
    )

    with pytest.raises(HouseholdAccessError, match="must be a member"):
        export_user_data(user=user, household_id=household.id)


@pytest.mark.django_db
@pytest.mark.unit
def test_request_data_deletion_marks_user_inactive():
    """Test deletion request marks user as inactive."""
    from privacy.services import request_data_deletion

    user = User.objects.create_user(
        email="delete@example.com",
        password="testpass123",
        first_name="Jane",
        last_name="Smith",
        phone_number="+1234567890",
    )

    result = request_data_deletion(user=user)

    user.refresh_from_db()

    assert user.is_active is False
    assert result["status"] == "pending"
    assert "deletion request has been recorded" in result["message"]


@pytest.mark.django_db
@pytest.mark.unit
def test_request_data_deletion_scrubs_pii():
    """Test deletion request removes PII fields."""
    from privacy.services import request_data_deletion

    user = User.objects.create_user(
        email="delete@example.com",
        password="testpass123",
        first_name="Jane",
        last_name="Smith",
        phone_number="+1234567890",
    )

    request_data_deletion(user=user)

    user.refresh_from_db()

    assert user.first_name == ""
    assert user.last_name == ""
    assert user.phone_number == ""
    # Email preserved as it's the key
    assert user.email == "delete@example.com"


@pytest.mark.django_db
@pytest.mark.unit
def test_request_data_deletion_idempotent():
    """Test multiple deletion requests are safe."""
    from privacy.services import request_data_deletion

    user = User.objects.create_user(
        email="delete@example.com",
        password="testpass123",
    )

    # Request deletion twice
    result1 = request_data_deletion(user=user)
    result2 = request_data_deletion(user=user)

    # Both should succeed
    assert result1["status"] == "pending"
    assert result2["status"] == "pending"

    # User should still be inactive
    user.refresh_from_db()
    assert user.is_active is False


@pytest.mark.django_db
@pytest.mark.unit
def test_get_data_deletion_status_active_user():
    """Test deletion status for active user."""
    from privacy.services import get_data_deletion_status

    user = User.objects.create_user(
        email="active@example.com",
        password="testpass123",
    )

    status = get_data_deletion_status(user=user)

    assert status["status"] == "rejected"
    assert "active" in status["message"].lower()
    assert "checked_at" in status


@pytest.mark.django_db
@pytest.mark.unit
def test_get_data_deletion_status_inactive_user():
    """Test deletion status for inactive user (deletion requested)."""
    from privacy.services import get_data_deletion_status

    user = User.objects.create_user(
        email="inactive@example.com",
        password="testpass123",
    )
    user.is_active = False
    user.save()

    status = get_data_deletion_status(user=user)

    assert status["status"] == "completed"
    assert "disabled" in status["message"].lower()
    assert "checked_at" in status
