"""
Tests for Transaction Splitting functionality.

Tests the ability to split transactions among household members,
supporting use cases like:
- Student flatmates splitting bills equally
- DINK couples splitting expenses proportionally (70/30)
- Families tracking individual member shares
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from apps.users.models import User
from apps.households.models import Household
from apps.accounts.models import Account
from apps.transactions.models import Transaction, TransactionSplit


@pytest.mark.django_db
class TestTransactionSplitCreate:
    """Test creating individual transaction splits."""

    @pytest.fixture
    def setup(self):
        """Set up test data."""
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
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
            amount=Decimal("-100.00"),
            description="Groceries",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        return {
            "household": household,
            "user": user,
            "account": account,
            "transaction": transaction,
            "client": client,
        }

    def test_create_single_split(self, setup):
        """Test creating a single transaction split."""
        response = setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {
                "amount": "50.00",
                "description": "My share of groceries",
                "member": setup["user"].id,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["amount"] == "50.00"
        assert response.data["description"] == "My share of groceries"
        assert response.data["member"] == setup["user"].id

        # Verify split was created in database
        assert (
            TransactionSplit.objects.filter(transaction=setup["transaction"]).count()
            == 1
        )

    def test_create_split_without_member(self, setup):
        """Test creating a split without assigning to a member."""
        response = setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {
                "amount": "30.00",
                "description": "Shared household expenses",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["amount"] == "30.00"
        assert response.data["member"] is None

    def test_create_split_with_category(self, setup):
        """Test creating a split with a category."""
        from categories.models import Category

        category = Category.objects.create(
            household=setup["household"],
            name="Food",
            category_type="expense",
        )

        response = setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {
                "amount": "40.00",
                "description": "Food portion",
                "category": category.id,
                "member": setup["user"].id,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["category"] == category.id
        assert response.data["category_name"] == "Food"

    def test_create_split_validation_zero_amount(self, setup):
        """Test validation prevents zero amount splits."""
        response = setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {
                "amount": "0.00",
                "member": setup["user"].id,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount" in response.data

    def test_create_split_validation_exceeds_total(self, setup):
        """Test validation prevents splits exceeding transaction amount."""
        # Create first split for $60
        setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {"amount": "60.00", "member": setup["user"].id},
        )

        # Try to create second split for $50 (total would be $110 > $100)
        response = setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {"amount": "50.00", "member": setup["user"].id},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cannot exceed" in str(response.data).lower()

    def test_create_multiple_splits_within_limit(self, setup):
        """Test creating multiple splits that sum correctly."""
        # Create three splits totaling $100
        setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {"amount": "40.00", "description": "Split 1"},
        )
        setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {"amount": "35.00", "description": "Split 2"},
        )
        response = setup["client"].post(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/",
            {"amount": "25.00", "description": "Split 3"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert (
            TransactionSplit.objects.filter(transaction=setup["transaction"]).count()
            == 3
        )


@pytest.mark.django_db
class TestTransactionSplitList:
    """Test listing transaction splits."""

    @pytest.fixture
    def setup(self):
        """Set up test data with splits."""
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
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
            amount=Decimal("-100.00"),
            description="Groceries",
            date=timezone.now(),
        )

        # Create some splits
        TransactionSplit.objects.create(
            transaction=transaction,
            member=user,
            amount=Decimal("50.00"),
            description="My share",
        )
        TransactionSplit.objects.create(
            transaction=transaction,
            member=user,
            amount=Decimal("30.00"),
            description="Another share",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        return {
            "household": household,
            "user": user,
            "transaction": transaction,
            "client": client,
        }

    def test_list_splits(self, setup):
        """Test listing all splits for a transaction."""
        response = setup["client"].get(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/"
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert response.data["total_split"] == Decimal("80.00")
        assert response.data["remaining"] == Decimal("20.00")
        assert len(response.data["splits"]) == 2

    def test_list_splits_empty(self):
        """Test listing splits for transaction with no splits."""
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
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
            amount=Decimal("-100.00"),
            description="Groceries",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/transactions/{transaction.uuid}/splits/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0
        assert response.data["total_split"] == 0
        assert response.data["remaining"] == Decimal("100.00")


@pytest.mark.django_db
class TestTransactionSplitEqually:
    """Test equal splitting functionality for flatmates."""

    @pytest.fixture
    def setup_flatmates(self):
        """Set up flatmate scenario (ICP4 - Students)."""
        household = Household.objects.create(name="Student Flat")

        # Create 3 flatmates
        flatmate1 = User.objects.create_user(
            email="flatmate1@test.com",
            password="testpass123",
            first_name="Alice",
            last_name="Student",
            household=household,
        )
        flatmate2 = User.objects.create_user(
            email="flatmate2@test.com",
            password="testpass123",
            first_name="Bob",
            last_name="Student",
            household=household,
        )
        flatmate3 = User.objects.create_user(
            email="flatmate3@test.com",
            password="testpass123",
            first_name="Charlie",
            last_name="Student",
            household=household,
        )

        account = Account.objects.create(
            household=household,
            name="Flat Account",
            account_type="checking",
            balance=Decimal("500.00"),
        )

        # Electricity bill to split
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-300.00"),
            description="Electricity bill",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=flatmate1)

        return {
            "household": household,
            "flatmates": [flatmate1, flatmate2, flatmate3],
            "transaction": transaction,
            "client": client,
        }

    def test_split_equally_among_three_flatmates(self, setup_flatmates):
        """Test equal split of electricity bill among 3 flatmates."""
        flatmate_ids = [f.id for f in setup_flatmates["flatmates"]]

        response = setup_flatmates["client"].post(
            f"/api/v1/transactions/{setup_flatmates['transaction'].uuid}/split-equally/",
            {
                "members": flatmate_ids,
                "split_type": "equal",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data["splits"]) == 3
        assert "split equal across 3 members" in response.data["message"].lower()

        # Verify each flatmate has a $100 split
        splits = TransactionSplit.objects.filter(
            transaction=setup_flatmates["transaction"]
        )
        assert splits.count() == 3

        for split in splits:
            assert split.amount == Decimal("100.00")
            assert split.member in setup_flatmates["flatmates"]
            assert "equal split" in split.description.lower()

    def test_split_equally_among_two(self, setup_flatmates):
        """Test equal split between 2 people (50/50)."""
        flatmate_ids = [
            setup_flatmates["flatmates"][0].id,
            setup_flatmates["flatmates"][1].id,
        ]

        response = setup_flatmates["client"].post(
            f"/api/v1/transactions/{setup_flatmates['transaction'].uuid}/split-equally/",
            {
                "members": flatmate_ids,
                "split_type": "equal",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify 50/50 split ($150 each)
        splits = TransactionSplit.objects.filter(
            transaction=setup_flatmates["transaction"]
        )
        assert splits.count() == 2

        for split in splits:
            assert split.amount == Decimal("150.00")

    def test_split_replaces_existing_splits(self, setup_flatmates):
        """Test that new split replaces old splits."""
        transaction = setup_flatmates["transaction"]

        # Create initial split
        TransactionSplit.objects.create(
            transaction=transaction,
            member=setup_flatmates["flatmates"][0],
            amount=Decimal("200.00"),
            description="Old split",
        )

        assert TransactionSplit.objects.filter(transaction=transaction).count() == 1

        # Create new equal split (should delete old one)
        flatmate_ids = [f.id for f in setup_flatmates["flatmates"]]

        response = setup_flatmates["client"].post(
            f"/api/v1/transactions/{transaction.uuid}/split-equally/",
            {
                "members": flatmate_ids,
                "split_type": "equal",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED

        # Verify old split was deleted and new splits created
        splits = TransactionSplit.objects.filter(transaction=transaction)
        assert splits.count() == 3
        assert not splits.filter(description="Old split").exists()

    def test_split_validation_members_not_in_household(self, setup_flatmates):
        """Test validation prevents splitting with users from other households."""
        # Create user in different household
        other_household = Household.objects.create(name="Other Household")
        other_user = User.objects.create_user(
            email="other@test.com",
            password="testpass123",
            household=other_household,
        )

        response = setup_flatmates["client"].post(
            f"/api/v1/transactions/{setup_flatmates['transaction'].uuid}/split-equally/",
            {
                "members": [setup_flatmates["flatmates"][0].id, other_user.id],
                "split_type": "equal",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "household" in str(response.data).lower()


@pytest.mark.django_db
class TestTransactionSplitProportional:
    """Test proportional splitting for DINK couples (70/30, 60/40, etc.)."""

    @pytest.fixture
    def setup_dink_couple(self):
        """Set up DINK couple scenario (ICP2)."""
        household = Household.objects.create(name="DINK Household")

        # Partner 1 (higher earner - 70%)
        partner1 = User.objects.create_user(
            email="partner1@test.com",
            password="testpass123",
            first_name="High",
            last_name="Earner",
            household=household,
        )

        # Partner 2 (lower earner - 30%)
        partner2 = User.objects.create_user(
            email="partner2@test.com",
            password="testpass123",
            first_name="Lower",
            last_name="Earner",
            household=household,
        )

        account = Account.objects.create(
            household=household,
            name="Joint Account",
            account_type="checking",
            balance=Decimal("5000.00"),
        )

        # Monthly rent to split proportionally
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-1000.00"),
            description="Monthly rent",
            date=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=partner1)

        return {
            "household": household,
            "partner1": partner1,
            "partner2": partner2,
            "transaction": transaction,
            "client": client,
        }

    def test_split_proportional_70_30(self, setup_dink_couple):
        """Test 70/30 proportional split for DINK couple."""
        response = setup_dink_couple["client"].post(
            f"/api/v1/transactions/{setup_dink_couple['transaction'].uuid}/split-equally/",
            {
                "members": [
                    setup_dink_couple["partner1"].id,
                    setup_dink_couple["partner2"].id,
                ],
                "split_type": "proportional",
                "proportions": {
                    str(setup_dink_couple["partner1"].id): 70.00,
                    str(setup_dink_couple["partner2"].id): 30.00,
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "split proportional across 2 members" in response.data["message"].lower()

        # Verify 70/30 split ($700 / $300)
        split1 = TransactionSplit.objects.get(
            transaction=setup_dink_couple["transaction"],
            member=setup_dink_couple["partner1"],
        )
        split2 = TransactionSplit.objects.get(
            transaction=setup_dink_couple["transaction"],
            member=setup_dink_couple["partner2"],
        )

        assert split1.amount == Decimal("700.00")
        assert "70" in split1.description and "%" in split1.description
        assert split2.amount == Decimal("300.00")
        assert "30" in split2.description and "%" in split2.description

    def test_split_proportional_60_40(self, setup_dink_couple):
        """Test 60/40 proportional split."""
        response = setup_dink_couple["client"].post(
            f"/api/v1/transactions/{setup_dink_couple['transaction'].uuid}/split-equally/",
            {
                "members": [
                    setup_dink_couple["partner1"].id,
                    setup_dink_couple["partner2"].id,
                ],
                "split_type": "proportional",
                "proportions": {
                    str(setup_dink_couple["partner1"].id): 60.00,
                    str(setup_dink_couple["partner2"].id): 40.00,
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED

        split1 = TransactionSplit.objects.get(
            transaction=setup_dink_couple["transaction"],
            member=setup_dink_couple["partner1"],
        )
        split2 = TransactionSplit.objects.get(
            transaction=setup_dink_couple["transaction"],
            member=setup_dink_couple["partner2"],
        )

        assert split1.amount == Decimal("600.00")
        assert split2.amount == Decimal("400.00")

    def test_split_proportional_validation_not_100_percent(self, setup_dink_couple):
        """Test validation requires proportions to sum to 100%."""
        response = setup_dink_couple["client"].post(
            f"/api/v1/transactions/{setup_dink_couple['transaction'].uuid}/split-equally/",
            {
                "members": [
                    setup_dink_couple["partner1"].id,
                    setup_dink_couple["partner2"].id,
                ],
                "split_type": "proportional",
                "proportions": {
                    str(setup_dink_couple["partner1"].id): 70.00,
                    str(setup_dink_couple["partner2"].id): 40.00,  # Sum = 110%
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "100" in str(response.data)

    def test_split_proportional_validation_missing_proportions(self, setup_dink_couple):
        """Test validation requires proportions for proportional split."""
        response = setup_dink_couple["client"].post(
            f"/api/v1/transactions/{setup_dink_couple['transaction'].uuid}/split-equally/",
            {
                "members": [
                    setup_dink_couple["partner1"].id,
                    setup_dink_couple["partner2"].id,
                ],
                "split_type": "proportional",
                # Missing proportions
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "proportion" in str(response.data).lower()

    def test_split_proportional_validation_missing_member_proportion(
        self, setup_dink_couple
    ):
        """Test validation requires proportion for each member."""
        response = setup_dink_couple["client"].post(
            f"/api/v1/transactions/{setup_dink_couple['transaction'].uuid}/split-equally/",
            {
                "members": [
                    setup_dink_couple["partner1"].id,
                    setup_dink_couple["partner2"].id,
                ],
                "split_type": "proportional",
                "proportions": {
                    str(setup_dink_couple["partner1"].id): 100.00,
                    # Missing partner2
                },
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestTransactionSplitDelete:
    """Test deleting transaction splits."""

    @pytest.fixture
    def setup(self):
        """Set up test data."""
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
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
            amount=Decimal("-100.00"),
            description="Groceries",
            date=timezone.now(),
        )

        split = TransactionSplit.objects.create(
            transaction=transaction,
            member=user,
            amount=Decimal("50.00"),
            description="My share",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        return {
            "transaction": transaction,
            "split": split,
            "client": client,
        }

    def test_delete_split(self, setup):
        """Test deleting a transaction split."""
        response = setup["client"].delete(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/{setup['split'].id}/"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TransactionSplit.objects.filter(id=setup["split"].id).exists()

    def test_delete_nonexistent_split(self, setup):
        """Test deleting a split that doesn't exist."""
        response = setup["client"].delete(
            f"/api/v1/transactions/{setup['transaction'].uuid}/splits/99999/"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestTransactionSplitPermissions:
    """Test permission controls for transaction splits."""

    def test_unauthenticated_cannot_create_split(self):
        """Test unauthenticated users cannot create splits."""
        household = Household.objects.create(name="Test Household")
        account = Account.objects.create(
            household=household,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        transaction = Transaction.objects.create(
            account=account,
            transaction_type="expense",
            amount=Decimal("-100.00"),
            description="Groceries",
            date=timezone.now(),
        )

        client = APIClient()
        # No authentication

        response = client.post(
            f"/api/v1/transactions/{transaction.uuid}/splits/",
            {"amount": "50.00"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_from_other_household_cannot_access_splits(self):
        """Test users cannot access splits from other households."""
        # Household 1
        household1 = Household.objects.create(name="Household 1")
        account1 = Account.objects.create(
            household=household1,
            name="Checking",
            account_type="checking",
            balance=Decimal("1000.00"),
        )
        transaction1 = Transaction.objects.create(
            account=account1,
            transaction_type="expense",
            amount=Decimal("-100.00"),
            description="Groceries",
            date=timezone.now(),
        )

        # Household 2 (different household)
        household2 = Household.objects.create(name="Household 2")
        user2 = User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
            household=household2,
        )

        client = APIClient()
        client.force_authenticate(user=user2)

        # Try to access household 1's transaction
        response = client.get(f"/api/v1/transactions/{transaction1.uuid}/splits/")

        # Should return 404 (transaction not visible to user2's household)
        assert response.status_code == status.HTTP_404_NOT_FOUND
