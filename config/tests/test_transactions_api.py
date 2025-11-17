import pytest
from datetime import datetime
from django.urls import reverse
from django.utils import timezone
from apps.accounts.models import Account
from apps.transactions.models import Transaction
from apps.households.models import Household, Membership


@pytest.mark.django_db
def test_user_cannot_create_transaction_on_other_household_account(
    auth_client, user, household
):
    # user is member of `household`
    other_household = Household.objects.create(name="Other Household")
    other_account = Account.objects.create(
        household=other_household,
        name="Other account",
        account_type="checking",
        currency="NZD",
    )

    url = reverse("transaction-list")
    resp = auth_client.post(
        url,
        {
            "account": other_account.id,
            "transaction_type": "expense",
            "amount": "10.00",
            "description": "Should not work",
            "date": "2025-01-01",
            "status": "completed",
        },
        format="json",
    )

    assert resp.status_code == 400
    assert "Account does not belong to your household" in str(resp.data)


@pytest.mark.django_db
def test_user_sees_only_own_household_transactions(auth_client, household, user):
    account = Account.objects.create(
        household=household,
        name="My account",
        account_type="checking",
        currency="NZD",
    )
    Transaction.objects.create(
        account=account,
        transaction_type="expense",
        amount="5.00",
        description="Visible",
        date=timezone.make_aware(datetime(2025, 1, 1)),
        status="completed",
    )

    other_household = Household.objects.create(name="Other")
    other_account = Account.objects.create(
        household=other_household,
        name="Other account",
        account_type="checking",
        currency="NZD",
    )
    Transaction.objects.create(
        account=other_account,
        transaction_type="expense",
        amount="99.00",
        description="Hidden",
        date=timezone.make_aware(datetime(2025, 1, 1)),
        status="completed",
    )

    url = reverse("transaction-list")
    resp = auth_client.get(url)

    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["description"] == "Visible"
