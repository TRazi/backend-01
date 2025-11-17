"""
Test suite for transaction serializers.
Tests validation logic and serialization behavior.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.transactions.models import Transaction, TransactionTag
from apps.transactions.serializers import (
    TransactionSerializer,
    TransactionCreateSerializer,
    TransactionTagSerializer,
    LinkTransferSerializer,
)
from apps.households.models import Household
from apps.accounts.models import Account
from apps.categories.models import Category

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestTransactionTagSerializer:
    """Test TransactionTagSerializer behavior."""

    def test_serializer_includes_all_fields(self):
        """Test that serializer includes all expected fields."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        tag = TransactionTag.objects.create(
            household=household, name="Business", color="#FF5733"
        )

        serializer = TransactionTagSerializer(tag)

        assert "id" in serializer.data
        assert "name" in serializer.data
        assert "color" in serializer.data
        assert "created_at" in serializer.data
        assert "updated_at" in serializer.data
        assert serializer.data["name"] == "Business"
        assert serializer.data["color"] == "#FF5733"


@pytest.mark.django_db
@pytest.mark.unit
class TestTransactionSerializer:
    """Test TransactionSerializer validation and behavior."""

    def test_get_is_transfer_true(self):
        """Test is_transfer returns True for transfer transactions."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="transfer",
            amount=Decimal("100.00"),
            description="Transfer",
            date=timezone.now(),
        )

        serializer = TransactionSerializer(transaction)
        assert serializer.data["is_transfer"] is True

    def test_get_is_transfer_false(self):
        """Test is_transfer returns False for non-transfer transactions."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("50.00"),
            description="Groceries",
            date=timezone.now(),
        )

        serializer = TransactionSerializer(transaction)
        assert serializer.data["is_transfer"] is False

    def test_get_linked_transaction_id(self):
        """Test linked_transaction_id returns correct ID when linked."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account1 = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        account2 = Account.objects.create(
            household=household,
            name="Savings",
            account_type="savings",
            balance=Decimal("500.00"),
        )

        # Create linked transfer
        transaction1 = Transaction.objects.create(
            account=account1,
            transaction_type="transfer",
            amount=Decimal("100.00"),
            description="Transfer to Savings",
            date=timezone.now(),
        )
        transaction2 = Transaction.objects.create(
            account=account2,
            transaction_type="transfer",
            amount=Decimal("100.00"),
            description="Transfer from Checking",
            date=timezone.now(),
            linked_transaction=transaction1,
        )

        serializer = TransactionSerializer(transaction2)
        assert serializer.data["linked_transaction_id"] == transaction1.id

    def test_validate_account_wrong_household(self):
        """Test validation fails when account belongs to different household."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        user.household = household1
        user.save()

        # Account from different household
        account = Account.objects.create(
            household=household2,
            name="Other Account",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        request = Mock()
        request.user = user

        serializer = TransactionSerializer(context={"request": request})

        with pytest.raises(Exception) as exc_info:
            serializer.validate_account(account)

        assert "does not belong to your household" in str(exc_info.value)

    def test_create_enforces_household(self):
        """Test create() enforces household validation."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        user.household = household1
        user.save()

        # Account from different household
        account = Account.objects.create(
            household=household2,
            name="Other Account",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        request = Mock()
        request.user = user

        serializer = TransactionSerializer(
            data={
                "account": account.id,
                "transaction_type": "expense",
                "amount": "50.00",
                "description": "Test",
                "date": timezone.now().isoformat(),
            },
            context={"request": request},
        )

        # Validation should fail
        assert not serializer.is_valid()


@pytest.mark.django_db
@pytest.mark.unit
class TestTransactionCreateSerializer:
    """Test TransactionCreateSerializer validation."""

    def test_validate_amount_positive(self):
        """Test validation passes for positive amounts."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        request = Mock()
        request.user = user

        serializer = TransactionCreateSerializer(
            data={
                "account": account.id,
                "transaction_type": "expense",
                "amount": "100.00",
                "description": "Groceries",
                "date": timezone.now().isoformat(),
            },
            context={"request": request},
        )

        assert serializer.is_valid()

    def test_validate_amount_negative_fails(self):
        """Test validation fails for negative amounts."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        request = Mock()
        request.user = user

        serializer = TransactionCreateSerializer(
            data={
                "account": account.id,
                "transaction_type": "expense",
                "amount": "-50.00",
                "description": "Invalid",
                "date": timezone.now().isoformat(),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "amount" in serializer.errors
        assert "positive value" in str(serializer.errors["amount"])

    def test_validate_amount_zero_fails(self):
        """Test validation fails for zero amounts."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        request = Mock()
        request.user = user

        serializer = TransactionCreateSerializer(
            data={
                "account": account.id,
                "transaction_type": "expense",
                "amount": "0.00",
                "description": "Invalid",
                "date": timezone.now().isoformat(),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "amount" in serializer.errors

    def test_validate_invalid_transaction_type(self):
        """Test validation fails for invalid transaction types."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        request = Mock()
        request.user = user

        serializer = TransactionCreateSerializer(
            data={
                "account": account.id,
                "transaction_type": "invalid",
                "amount": "100.00",
                "description": "Test",
                "date": timezone.now().isoformat(),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "transaction_type" in serializer.errors

    def test_update_prevents_account_change(self):
        """Test update() prevents changing the account."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        account1 = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        account2 = Account.objects.create(
            household=household,
            name="Savings",
            account_type="savings",
            balance=Decimal("500.00"),
        )

        transaction = Transaction.objects.create(
            account=account1,
            transaction_type="expense",
            amount=Decimal("50.00"),
            description="Original",
            date=timezone.now(),
        )

        request = Mock()
        request.user = user

        serializer = TransactionCreateSerializer(
            instance=transaction,
            data={
                "account": account2.id,  # Try to change account
                "amount": "75.00",
                "description": "Updated",
            },
            partial=True,
            context={"request": request},
        )

        if serializer.is_valid():
            updated = serializer.save()
            # Account should NOT have changed
            assert updated.account == account1
            assert updated.account != account2


@pytest.mark.django_db
@pytest.mark.unit
class TestLinkTransferSerializer:
    """Test LinkTransferSerializer validation."""

    def test_serializer_validates_required_fields(self):
        """Test serializer requires destination_account."""
        serializer = LinkTransferSerializer(data={})

        assert not serializer.is_valid()
        assert "destination_account" in serializer.errors

    def test_serializer_accepts_valid_data(self):
        """Test serializer accepts valid transfer link data."""
        serializer = LinkTransferSerializer(
            data={
                "destination_account": 123,
                "amount": "100.00",
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["destination_account"] == 123
        assert serializer.validated_data["amount"] == Decimal("100.00")

    def test_serializer_amount_optional(self):
        """Test amount field is optional."""
        serializer = LinkTransferSerializer(
            data={
                "destination_account": 456,
            }
        )

        assert serializer.is_valid()
        assert serializer.validated_data["destination_account"] == 456
        assert "amount" not in serializer.validated_data
