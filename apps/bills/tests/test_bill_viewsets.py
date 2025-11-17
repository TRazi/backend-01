"""
Tests for Bill ViewSet API endpoints.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import timedelta

from apps.users.models import User
from apps.households.models import Household
from apps.accounts.models import Account
from apps.categories.models import Category
from apps.bills.models import Bill


@pytest.mark.django_db
class TestBillViewSetList:
    """Test bill list endpoint."""

    def test_list_bills_authenticated(self):
        """Authenticated user can list their household's bills."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        Bill.objects.create(
            household=household,
            name="Rent",
            amount=Decimal("1200.00"),
            due_date=timezone.now().date(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/bills/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Rent"

    def test_list_bills_unauthenticated(self):
        """Unauthenticated users cannot list bills."""
        client = APIClient()
        response = client.get("/api/v1/bills/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_bills_household_isolation(self):
        """Users only see bills from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        Bill.objects.create(
            household=household1,
            name="Family 1 Bill",
            amount=100,
            due_date=timezone.now().date(),
        )
        Bill.objects.create(
            household=household2,
            name="Family 2 Bill",
            amount=200,
            due_date=timezone.now().date(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/bills/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Family 1 Bill"

    def test_list_bills_staff_sees_all(self):
        """Staff users can see all bills."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        staff_user = User.objects.create_user(
            email="staff@test.com",
            password="pass123",
            first_name="Staff",
            household=household1,
            is_staff=True,
        )

        Bill.objects.create(
            household=household1,
            name="Bill 1",
            amount=100,
            due_date=timezone.now().date(),
        )
        Bill.objects.create(
            household=household2,
            name="Bill 2",
            amount=200,
            due_date=timezone.now().date(),
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/bills/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestBillViewSetCreate:
    """Test bill creation endpoint."""

    def test_create_bill_valid(self):
        """Can create a valid bill."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "name": "Internet Bill",
            "amount": "80.00",
            "due_date": (timezone.now() + timedelta(days=10)).date().isoformat(),
            "frequency": "monthly",
            "is_recurring": True,
        }

        response = client.post("/api/v1/bills/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Internet Bill"
        assert Decimal(response.data["amount"]) == Decimal("80.00")
        assert response.data["household"] == household.id

    def test_create_bill_with_category_and_account(self):
        """Can create bill with category and account."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        category = Category.objects.create(
            household=household, name="Utilities", category_type="expense"
        )
        account = Account.objects.create(
            household=household, name="Checking", account_type="checking", balance=1000
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "name": "Electric Bill",
            "amount": "120.00",
            "due_date": timezone.now().date().isoformat(),
            "category": category.id,
            "account": account.id,
        }

        response = client.post("/api/v1/bills/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == category.id
        assert response.data["account"] == account.id


@pytest.mark.django_db
class TestBillViewSetUpdate:
    """Test bill update endpoint."""

    def test_update_bill_valid(self):
        """Can update a bill."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        bill = Bill.objects.create(
            household=household,
            name="Old Name",
            amount=Decimal("100.00"),
            due_date=timezone.now().date(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "name": "New Name",
            "amount": "150.00",
            "due_date": timezone.now().date().isoformat(),
        }

        response = client.patch(f"/api/v1/bills/{bill.id}/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"
        assert Decimal(response.data["amount"]) == Decimal("150.00")

    def test_update_bill_different_household_denied(self):
        """Cannot update bill from different household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        bill2 = Bill.objects.create(
            household=household2,
            name="Bill",
            amount=100,
            due_date=timezone.now().date(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)

        data = {"name": "Updated"}
        response = client.patch(f"/api/v1/bills/{bill2.id}/", data)

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.mark.django_db
class TestBillViewSetDelete:
    """Test bill deletion endpoint."""

    def test_delete_bill_valid(self):
        """Can delete own household's bill."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        bill = Bill.objects.create(
            household=household, name="Bill", amount=100, due_date=timezone.now().date()
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/bills/{bill.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Bill.objects.filter(id=bill.id).exists()


@pytest.mark.django_db
class TestBillMarkPaidAction:
    """Test mark_paid custom action."""

    def test_mark_bill_as_paid(self):
        """Can mark a bill as paid."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        bill = Bill.objects.create(
            household=household,
            name="Rent",
            amount=Decimal("1200.00"),
            due_date=timezone.now().date(),
            status="pending",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"paid_date": timezone.now().date().isoformat()}
        response = client.post(
            f"/api/v1/bills/{bill.id}/mark-paid/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "paid"

        bill.refresh_from_db()
        assert bill.status == "paid"
        assert bill.paid_date is not None

    def test_mark_paid_uses_current_date_if_not_provided(self):
        """Mark paid uses current date if paid_date not provided."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        bill = Bill.objects.create(
            household=household,
            name="Bill",
            amount=100,
            due_date=timezone.now().date(),
            status="pending",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.post(f"/api/v1/bills/{bill.id}/mark-paid/", {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        bill.refresh_from_db()
        assert bill.status == "paid"
        assert bill.paid_date == timezone.now().date()

    def test_mark_paid_with_transaction_link(self):
        """Can mark paid and link to a transaction."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        # Create account and transaction first
        from accounts.models import Account
        from transactions.models import Transaction

        account = Account.objects.create(
            household=household,
            name="Test Account",
            account_type="checking",
            balance=1000,
        )

        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("100.00"),
            description="Bill payment",
            date=timezone.now(),
        )

        bill = Bill.objects.create(
            household=household,
            name="Bill",
            amount=100,
            due_date=timezone.now().date(),
            status="pending",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"transaction": transaction.id}
        response = client.post(
            f"/api/v1/bills/{bill.id}/mark-paid/", data, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        bill.refresh_from_db()
        assert bill.status == "paid"
        assert bill.transaction_id == transaction.id


@pytest.mark.django_db
class TestBillUpcomingAction:
    """Test upcoming_bills custom action."""

    def test_upcoming_bills_returns_upcoming_only(self):
        """Upcoming bills action returns only upcoming bills."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        # Upcoming bill (within 7 days)
        Bill.objects.create(
            household=household,
            name="Upcoming",
            amount=100,
            due_date=(timezone.now() + timedelta(days=3)).date(),
            status="pending",
        )

        # Not upcoming (too far)
        Bill.objects.create(
            household=household,
            name="Future",
            amount=100,
            due_date=(timezone.now() + timedelta(days=30)).date(),
            status="pending",
        )

        # Paid bill
        Bill.objects.create(
            household=household,
            name="Paid",
            amount=100,
            due_date=timezone.now().date(),
            status="paid",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/bills/upcoming/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Upcoming"


@pytest.mark.django_db
class TestBillOverdueAction:
    """Test overdue_bills custom action."""

    def test_overdue_bills_returns_overdue_only(self):
        """Overdue bills action returns only overdue bills."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        # Overdue bill
        Bill.objects.create(
            household=household,
            name="Overdue",
            amount=100,
            due_date=(timezone.now() - timedelta(days=5)).date(),
            status="pending",
        )

        # Future bill
        Bill.objects.create(
            household=household,
            name="Future",
            amount=100,
            due_date=(timezone.now() + timedelta(days=10)).date(),
            status="pending",
        )

        # Paid bill
        Bill.objects.create(
            household=household,
            name="Paid",
            amount=100,
            due_date=(timezone.now() - timedelta(days=2)).date(),
            status="paid",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/bills/overdue/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Overdue"
