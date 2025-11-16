"""
Tests for transaction service functions.
"""

import pytest
from decimal import Decimal
from datetime import date
from unittest.mock import Mock
from django.utils import timezone

from transactions.models import Transaction
from transactions.services import (
    transaction_create,
    transaction_update,
    transaction_delete,
)
from accounts.models import Account
from categories.models import Category
from households.models import Household
from users.models import User


@pytest.mark.django_db
@pytest.mark.unit
def test_transaction_create():
    """Test creating a transaction updates account balance."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
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

    # Mock request
    request = Mock()
    request.user = user
    request.path = "/api/transactions/"
    request.method = "POST"
    request.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "Test"}

    transaction = transaction_create(
        account=account,
        amount=Decimal("100.50"),
        description="Test transaction",
        transaction_type="income",
        transaction_date=timezone.now(),
        request=request,
    )

    assert transaction.account == account
    assert transaction.amount == Decimal("100.50")
    assert transaction.description == "Test transaction"
    assert transaction.transaction_type == "income"

    # Check account balance updated
    account.refresh_from_db()
    assert account.balance == Decimal("1100.50")


@pytest.mark.django_db
@pytest.mark.unit
def test_transaction_create_with_category():
    """Test creating a transaction with category."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
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
        name="Groceries",
        category_type="ex",
        household=household,
    )

    request = Mock()
    request.user = user
    request.path = "/api/transactions/"
    request.method = "POST"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    transaction = transaction_create(
        account=account,
        amount=Decimal("-50.00"),
        description="Grocery shopping",
        transaction_type="expense",
        category=category,
        transaction_date=timezone.now(),
        request=request,
    )

    assert transaction.category == category
    assert transaction.amount == Decimal("-50.00")
    assert transaction.transaction_type == "expense"


@pytest.mark.django_db
@pytest.mark.unit
def test_transaction_update():
    """Test updating a transaction."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
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

    transaction = Transaction.objects.create(
        account=account,
        amount=Decimal("100.00"),
        description="Original description",
        transaction_type="income",
        date=timezone.now(),
    )

    request = Mock()
    request.user = user
    request.path = f"/api/transactions/{transaction.id}/"
    request.method = "PATCH"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    updated = transaction_update(
        transaction_id=transaction.id,
        request=request,
        description="Updated description",
        amount=Decimal("150.00"),
    )

    assert updated.description == "Updated description"
    assert updated.amount == Decimal("150.00")


@pytest.mark.django_db
@pytest.mark.unit
def test_transaction_delete():
    """Test deleting a transaction updates account balance."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
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

    transaction = Transaction.objects.create(
        account=account,
        amount=Decimal("100.00"),
        description="To be deleted",
        transaction_type="income",
        date=timezone.now(),
    )

    # Account balance should have been updated
    account.balance = Decimal("1100.00")
    account.save()

    request = Mock()
    request.user = user
    request.path = f"/api/transactions/{transaction.id}/"
    request.method = "DELETE"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    transaction_delete(
        transaction_id=transaction.id,
        request=request,
    )

    # Check transaction deleted
    assert not Transaction.objects.filter(pk=transaction.id).exists()

    # Check account balance restored
    account.refresh_from_db()
    assert account.balance == Decimal("1000.00")


@pytest.mark.django_db
@pytest.mark.unit
def test_transaction_create_with_date():
    """Test creating a transaction with specific date."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
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

    request = Mock()
    request.user = user
    request.path = "/api/transactions/"
    request.method = "POST"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    specific_date = timezone.make_aware(timezone.datetime(2025, 1, 15))
    transaction = transaction_create(
        account=account,
        amount=Decimal("200.00"),
        description="Past transaction",
        transaction_type="income",
        transaction_date=specific_date,
        request=request,
    )

    assert transaction.date == specific_date
