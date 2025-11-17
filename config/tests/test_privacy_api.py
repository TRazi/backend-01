import pytest
from django.urls import reverse

from apps.households.models import Household, Membership


@pytest.mark.django_db
def test_data_export_requires_household_membership(auth_client, user):
    household = Household.objects.create(name="Some Household")

    # no membership created -> should 404/deny
    url = reverse("privacy:data-export")
    resp = auth_client.get(url, {"household_id": household.id})

    assert resp.status_code in (403, 404)  # we deliberately blur for privacy


@pytest.mark.django_db
def test_data_export_succeeds_for_member(auth_client, user, household, membership):
    url = reverse("privacy:data-export")
    resp = auth_client.get(url, {"household_id": household.id})

    assert resp.status_code == 200
    assert resp.data["metadata"]["household_id"] == household.id
    assert resp.data["user"]["email"] == user.email
