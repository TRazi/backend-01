"""
Integration tests for Organisation ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.organisations.models import Organisation


@pytest.mark.django_db
class TestOrganisationViewSetList:
    """Test organisation list endpoint."""

    def test_list_organisations_as_admin(self):
        """Admin users can list all organisations."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        Organisation.objects.create(
            name="Org 1",
            subscription_tier="ww_starter",
            payment_status="active",
            owner=admin_user,
            contact_email="org1@test.com",
        )
        Organisation.objects.create(
            name="Org 2",
            subscription_tier="ww_enterprise",
            payment_status="active",
            owner=admin_user,
            contact_email="org2@test.com",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/organisations/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_list_organisations_as_regular_user(self):
        """Regular users cannot access organisations."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/organisations/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_organisations_unauthenticated(self):
        """Unauthenticated users cannot access organisations."""
        client = APIClient()
        response = client.get("/api/v1/organisations/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_active_status(self):
        """Admin can filter organisations by active status."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        Organisation.objects.create(
            name="Active Org",
            is_active=True,
            owner=admin_user,
            contact_email="active@test.com",
        )
        Organisation.objects.create(
            name="Inactive Org",
            is_active=False,
            owner=admin_user,
            contact_email="inactive@test.com",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/organisations/?active=true")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Active Org"

    def test_filter_by_subscription_tier(self):
        """Admin can filter organisations by subscription tier."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        Organisation.objects.create(
            name="Basic Org",
            subscription_tier="ww_starter",
            owner=admin_user,
            contact_email="basic@test.com",
        )
        Organisation.objects.create(
            name="Premium Org",
            subscription_tier="ww_enterprise",
            owner=admin_user,
            contact_email="premium@test.com",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/organisations/?subscription_tier=ww_enterprise")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Premium Org"

    def test_filter_by_payment_status(self):
        """Admin can filter organisations by payment status."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        Organisation.objects.create(
            name="Active Org",
            payment_status="active",
            owner=admin_user,
            contact_email="active@test.com",
        )
        Organisation.objects.create(
            name="Suspended Org",
            payment_status="suspended",
            owner=admin_user,
            contact_email="suspended@test.com",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/organisations/?payment_status=suspended")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Suspended Org"


@pytest.mark.django_db
class TestOrganisationViewSetCreate:
    """Test organisation create endpoint."""

    def test_create_organisation_as_admin(self):
        """Admin users can create organisations."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post(
            "/api/v1/organisations/",
            {
                "name": "New Organisation",
                "contact_email": "contact@neworg.com",
                "owner": admin_user.id,
                "subscription_tier": "ww_starter",
                "payment_status": "active",
                "max_households": 10,
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Organisation"
        assert Organisation.objects.count() == 1

    def test_create_organisation_as_regular_user(self):
        """Regular users cannot create organisations."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/organisations/",
            {
                "name": "New Organisation",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Organisation.objects.count() == 0


@pytest.mark.django_db
class TestOrganisationViewSetUpdate:
    """Test organisation update endpoint."""

    def test_update_organisation_as_admin(self):
        """Admin users can update organisations."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        org = Organisation.objects.create(
            name="Original Name",
            subscription_tier="ww_starter",
            owner=admin_user,
            contact_email="org@test.com",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.patch(
            f"/api/v1/organisations/{org.id}/",
            {
                "name": "Updated Name",
                "subscription_tier": "ww_enterprise",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Name"
        assert response.data["subscription_tier"] == "ww_enterprise"

    def test_update_organisation_as_regular_user(self):
        """Regular users cannot update organisations."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        org = Organisation.objects.create(
            name="Test Org", owner=admin_user, contact_email="test@test.com"
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/v1/organisations/{org.id}/",
            {
                "name": "Hacked Name",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestOrganisationViewSetDelete:
    """Test organisation delete endpoint."""

    def test_delete_organisation_as_admin(self):
        """Admin users can delete organisations."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        org = Organisation.objects.create(
            name="To Delete", owner=admin_user, contact_email="delete@test.com"
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.delete(f"/api/v1/organisations/{org.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Organisation.objects.count() == 0

    def test_delete_organisation_as_regular_user(self):
        """Regular users cannot delete organisations."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        org = Organisation.objects.create(
            name="Test Org", owner=admin_user, contact_email="test@test.com"
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/organisations/{org.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Organisation.objects.count() == 1
