"""
Tests for Account ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from apps.users.models import User
from apps.households.models import Household
from apps.accounts.models import Account


@pytest.mark.django_db
class TestAccountViewSetList:
    """Test account list endpoint."""

    def test_list_accounts_authenticated(self):
        """Authenticated user can list their household's accounts."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/accounts/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Checking"

    def test_list_accounts_unauthenticated(self):
        """Unauthenticated users cannot list accounts."""
        client = APIClient()
        response = client.get("/api/v1/accounts/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_accounts_household_isolation(self):
        """Users only see accounts from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        Account.objects.create(
            household=household1,
            name="Family 1 Account",
            account_type="checking",
            balance=1000,
        )
        Account.objects.create(
            household=household2,
            name="Family 2 Account",
            account_type="checking",
            balance=1000,
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/accounts/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Family 1 Account"

    def test_staff_sees_all_accounts(self):
        """Staff users can see all accounts."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        staff_user = User.objects.create_user(
            email="staff@test.com",
            password="pass123",
            first_name="Staff",
            household=household1,
            is_staff=True,
        )

        Account.objects.create(
            household=household1, name="Acc 1", account_type="checking", balance=100
        )
        Account.objects.create(
            household=household2, name="Acc 2", account_type="checking", balance=200
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/accounts/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestAccountViewSetCreate:
    """Test account creation endpoint."""

    def test_create_account_valid(self):
        """Can create a valid account."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"name": "Savings Account", "account_type": "savings", "currency": "USD"}

        response = client.post("/api/v1/accounts/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Savings Account"
        # Verify account was created with default balance of 0
        created_account = Account.objects.get(
            name="Savings Account", household=household
        )
        assert created_account.balance == Decimal("0.00")
        assert created_account.household == household


@pytest.mark.django_db
class TestAccountViewSetUpdate:
    """Test account update endpoint."""

    def test_update_account_valid(self):
        """Can update an account."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household,
            name="Old Name",
            account_type="checking",
            balance=Decimal("1000.00"),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"name": "New Name"}
        response = client.patch(f"/api/v1/accounts/{account.uuid}/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"

    def test_update_account_different_household_denied(self):
        """Cannot update account from different household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        account2 = Account.objects.create(
            household=household2, name="Account", account_type="checking", balance=1000
        )

        client = APIClient()
        client.force_authenticate(user=user1)

        data = {"name": "Updated"}
        response = client.patch(f"/api/v1/accounts/{account2.id}/", data)

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.mark.django_db
class TestAccountViewSetDelete:
    """Test account deletion endpoint."""

    def test_delete_account_valid(self):
        """Can delete own household's account."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        account = Account.objects.create(
            household=household, name="To Delete", account_type="checking", balance=0
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/accounts/{account.uuid}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Account.objects.filter(id=account.id).exists()


@pytest.mark.django_db
class TestAccountCloseAction:
    """Test close_account custom action."""

    def test_close_account(self):
        """Can close an account."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("100.00"),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f"/api/v1/accounts/{account.uuid}/close/")

        assert response.status_code == status.HTTP_200_OK
        # Verify account was closed (excluded from totals)
        account.refresh_from_db()
        assert account.include_in_totals is False
