"""
Tests for Transaction ViewSet API endpoints.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from apps.users.models import User
from apps.households.models import Household
from apps.accounts.models import Account
from apps.categories.models import Category
from apps.transactions.models import Transaction, TransactionTag


@pytest.mark.django_db
class TestTransactionViewSetList:
    """Test transaction list endpoint."""

    def test_list_transactions_authenticated(self):
        """Authenticated user can list their household's transactions."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        Transaction.objects.create(
            account=account,
            transaction_type="income",
            amount=Decimal("100.00"),
            description="Salary",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/transactions/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["description"] == "Salary"

    def test_list_transactions_unauthenticated(self):
        """Unauthenticated users cannot list transactions."""
        client = APIClient()
        response = client.get("/api/v1/transactions/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_transactions_household_isolation(self):
        """Users only see transactions from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )
        User.objects.create_user(
            email="user2@test.com",
            password="pass123",
            first_name="User2",
            household=household2,
        )

        account1 = Account.objects.create(
            household=household1,
            name="Account1",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        account2 = Account.objects.create(
            household=household2,
            name="Account2",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        Transaction.objects.create(
            account=account1,
            transaction_type="income",
            amount=Decimal("100.00"),
            description="Household 1 transaction",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account2,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Household 2 transaction",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/transactions/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["description"] == "Household 1 transaction"

    def test_list_transactions_staff_sees_all(self):
        """Staff users can see all transactions."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        staff_user = User.objects.create_user(
            email="staff@test.com",
            password="pass123",
            first_name="Staff",
            household=household1,
            is_staff=True,
        )

        account1 = Account.objects.create(
            household=household1, name="Acc1", account_type="checking", balance=0
        )
        account2 = Account.objects.create(
            household=household2, name="Acc2", account_type="checking", balance=0
        )

        Transaction.objects.create(
            account=account1,
            transaction_type="income",
            amount=100,
            description="T1",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account2,
            transaction_type="income",
            amount=200,
            description="T2",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/transactions/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestTransactionViewSetCreate:
    """Test transaction creation endpoint."""

    def test_create_transaction_valid(self):
        """Can create a valid transaction."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "account": account.id,
            "transaction_type": "expense",
            "amount": "50.00",  # Positive amount, sign determined by transaction_type
            "description": "Groceries",
            "date": timezone.now().isoformat(),
        }

        response = client.post("/api/v1/transactions/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["description"] == "Groceries"
        assert Decimal(response.data["amount"]) == Decimal("50.00")

    def test_create_transaction_with_category(self):
        """Can create transaction with category."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        category = Category.objects.create(
            household=household, name="Food", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "account": account.id,
            "transaction_type": "expense",
            "amount": "75.00",
            "description": "Restaurant",
            "date": timezone.now().isoformat(),
            "category": category.id,
        }

        response = client.post("/api/v1/transactions/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == category.id


@pytest.mark.django_db
class TestTransactionViewSetUpdate:
    """Test transaction update endpoint."""

    def test_update_transaction_valid(self):
        """Can update a transaction."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-50.00"),
            description="Old description",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "account": account.id,
            "transaction_type": "expense",
            "amount": "75.00",
            "description": "New description",
            "date": timezone.now().isoformat(),
        }

        response = client.put(f"/api/v1/transactions/{transaction.uuid}/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["description"] == "New description"

    def test_update_transaction_different_household_denied(self):
        """Cannot update transaction from different household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )
        User.objects.create_user(
            email="user2@test.com",
            password="pass123",
            first_name="User2",
            household=household2,
        )

        account2 = Account.objects.create(
            household=household2, name="Acc2", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account2,
            transaction_type="income",
            amount=100,
            description="Test",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)

        data = {
            "account": account2.id,
            "transaction_type": "income",
            "amount": "200.00",
            "description": "Updated",
            "date": timezone.now().isoformat(),
        }

        response = client.put(f"/api/v1/transactions/{transaction.id}/", data)

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.mark.django_db
class TestTransactionViewSetDelete:
    """Test transaction deletion endpoint."""

    def test_delete_transaction_valid(self):
        """Can delete own household's transaction."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="To delete",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/transactions/{transaction.uuid}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Transaction.objects.filter(id=transaction.id).exists()


@pytest.mark.django_db
class TestTransactionLinkTransferAction:
    """Test link_transfer custom action."""

    def test_link_transfer_creates_opposite_transaction(self):
        """Link transfer creates opposite transaction in destination account."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        source_account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )
        dest_account = Account.objects.create(
            household=household, name="Savings", account_type="savings", balance=500
        )

        source_tx = Transaction.objects.create(
            account=source_account,
            transaction_type="expense",
            amount=-100,
            description="Transfer out",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"destination_account": dest_account.id, "amount": "100.00"}

        response = client.post(
            f"/api/v1/transactions/{source_tx.uuid}/link-transfer/", data
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["transaction_type"] == "income"
        assert Decimal(response.data["amount"]) == Decimal("100.00")

        # Verify source transaction is linked
        source_tx.refresh_from_db()
        assert source_tx.linked_transaction is not None

    def test_link_transfer_different_household_denied(self):
        """Cannot link transfer to account in different household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household1,
        )

        source_account = Account.objects.create(
            household=household1, name="Checking", account_type="checking", balance=1000
        )
        dest_account = Account.objects.create(
            household=household2, name="Savings", account_type="savings", balance=500
        )

        source_tx = Transaction.objects.create(
            account=source_account,
            transaction_type="expense",
            amount=-100,
            description="Transfer",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"destination_account": dest_account.id}
        response = client.post(
            f"/api/v1/transactions/{source_tx.uuid}/link-transfer/", data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_link_transfer_uses_default_amount(self):
        """Link transfer uses source amount if not specified."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        source_account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )
        dest_account = Account.objects.create(
            household=household, name="Savings", account_type="savings", balance=500
        )

        source_tx = Transaction.objects.create(
            account=source_account,
            transaction_type="expense",
            amount=Decimal("-150.00"),
            description="Transfer",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"destination_account": dest_account.id}
        response = client.post(
            f"/api/v1/transactions/{source_tx.uuid}/link-transfer/", data, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        # The stored amount matches the source (negative for expense, positive for income)
        assert abs(Decimal(response.data["amount"])) == Decimal("150.00")


@pytest.mark.django_db
class TestTransactionTagActions:
    """Test add_tags and remove_tag actions."""

    def test_add_tags_to_transaction(self):
        """Can add tags to transaction."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Grocery",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"tags": ["groceries", "essential"]}
        response = client.post(
            f"/api/v1/transactions/{transaction.uuid}/tags/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        transaction.refresh_from_db()
        assert transaction.tags.count() == 2

    def test_add_tags_creates_new_tags(self):
        """Adding tags creates them if they don't exist."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Test",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"tags": ["new-tag"]}
        response = client.post(
            f"/api/v1/transactions/{transaction.uuid}/tags/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert TransactionTag.objects.filter(
            household=household, name="new-tag"
        ).exists()

    def test_add_tags_invalid_format(self):
        """Adding tags with invalid format returns error."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Test",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"tags": "not-a-list"}
        response = client.post(f"/api/v1/transactions/{transaction.uuid}/tags/", data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_tag_from_transaction(self):
        """Can remove tag from transaction."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Test",
            date=timezone.now(),
        )
        tag = TransactionTag.objects.create(household=household, name="test-tag")
        transaction.tags.add(tag)

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"tag_id": tag.id}
        response = client.post(
            f"/api/v1/transactions/{transaction.uuid}/remove-tag/", data
        )

        assert response.status_code == status.HTTP_200_OK
        transaction.refresh_from_db()
        assert transaction.tags.count() == 0

    def test_remove_tag_missing_id(self):
        """Removing tag without ID returns error."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Test",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f"/api/v1/transactions/{transaction.uuid}/remove-tag/", {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTransactionStubActions:
    """Test stub actions (OCR, voice)."""

    def test_receipt_ocr_returns_placeholder(self):
        """Receipt OCR returns placeholder response."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/transactions/receipt-ocr/")

        assert response.status_code == status.HTTP_200_OK
        assert "placeholder" in response.data["message"].lower()

    def test_voice_input_returns_placeholder(self):
        """Voice input returns placeholder response."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/transactions/voice/")

        assert response.status_code == status.HTTP_200_OK
        assert "placeholder" in response.data["message"].lower()


@pytest.mark.django_db
class TestTransactionFiltering:
    """Test transaction filtering and search."""

    def test_filter_by_transaction_type(self):
        """Can filter transactions by type."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        Transaction.objects.create(
            account=account,
            transaction_type="income",
            amount=100,
            description="Salary",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Groceries",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/transactions/?transaction_type=income")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["transaction_type"] == "income"

    def test_search_transactions(self):
        """Can search transactions by description."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=0
        )

        Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-50,
            description="Grocery store",
            date=timezone.now(),
        )
        Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=-100,
            description="Restaurant",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/transactions/?search=grocery")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert "grocery" in response.data[0]["description"].lower()
