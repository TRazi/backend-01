"""
Tests for household APIs (apps/households/apis.py).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from households.models import Household, Membership

User = get_user_model()


@pytest.mark.django_db
class TestHouseholdListCreateApi:
    """Test HouseholdListCreateApi view."""

    def test_list_households_authenticated_user_with_household(self):
        """Test listing households for user with household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/households/households/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Test Household"

    def test_list_households_authenticated_user_without_household(self):
        """Test listing households for user without household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/households/households/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_list_households_unauthenticated(self):
        """Test listing households requires authentication."""
        client = APIClient()
        response = client.get("/api/v1/households/households/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_household_authenticated(self):
        """Test creating household when authenticated."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/households/households/",
            {"name": "New Household"},
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Household"
        assert Household.objects.filter(name="New Household").exists()

    def test_create_household_unauthenticated(self):
        """Test creating household requires authentication."""
        client = APIClient()
        response = client.post(
            "/api/v1/households/households/",
            {"name": "New Household"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_household_uses_create_serializer(self):
        """Test POST uses HouseholdCreateSerializer."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/households/households/", {"name": "Test"})

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestHouseholdDetailApi:
    """Test HouseholdDetailApi view."""

    def test_retrieve_household(self):
        """Test retrieving a household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/households/households/{household.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Test Household"

    def test_update_household(self):
        """Test updating a household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Old Name")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/v1/households/households/{household.id}/",
            {"name": "New Name"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"

        household.refresh_from_db()
        assert household.name == "New Name"

    def test_delete_household(self):
        """Test deleting a household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="To Delete")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/households/households/{household.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Household.objects.filter(id=household.id).exists()

    def test_retrieve_household_unauthenticated(self):
        """Test retrieving household requires authentication."""
        household = Household.objects.create(name="Test Household")

        client = APIClient()
        response = client.get(f"/api/v1/households/households/{household.id}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestMembershipListApi:
    """Test MembershipListApi view."""

    def test_list_memberships_with_household(self):
        """Test listing memberships for user with household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        Membership.objects.create(
            household=household,
            user=user,
            role="admin",
            status="active",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/households/memberships/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["user"] == user.id

    def test_list_memberships_without_household(self):
        """Test listing memberships for user without household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/households/memberships/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 0

    def test_list_memberships_unauthenticated(self):
        """Test listing memberships requires authentication."""
        client = APIClient()
        response = client.get("/api/v1/households/memberships/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_memberships_filters_by_household(self):
        """Test memberships are filtered to user's household."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        user.household = household1
        user.save()

        Membership.objects.create(
            household=household1,
            user=user,
            role="admin",
            status="active",
        )

        user2 = User.objects.create_user(email="other@example.com", password="pass123")
        Membership.objects.create(
            household=household2,
            user=user2,
            role="member",
            status="active",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/households/memberships/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["user"] == user.id


@pytest.mark.django_db
class TestMembershipCreateApi:
    """Test MembershipCreateApi view."""

    def test_create_membership(self):
        """Test creating a membership."""
        user = User.objects.create_user(email="admin@example.com", password="pass123")
        new_user = User.objects.create_user(
            email="member@example.com", password="pass123"
        )
        household = Household.objects.create(name="Test Household")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/households/memberships/create/",
            {
                "household": household.id,
                "user": new_user.id,
                "role": "observer",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert Membership.objects.filter(household=household, user=new_user).exists()

    def test_create_membership_unauthenticated(self):
        """Test creating membership requires authentication."""
        client = APIClient()
        response = client.post(
            "/api/v1/households/memberships/create/",
            {"household": 1, "user": 1, "role": "observer"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_membership_uses_create_serializer(self):
        """Test POST uses MembershipCreateSerializer."""
        user = User.objects.create_user(email="admin@example.com", password="pass123")
        new_user = User.objects.create_user(
            email="member@example.com", password="pass123"
        )
        household = Household.objects.create(name="Test Household")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/households/memberships/create/",
            {
                "household": household.id,
                "user": new_user.id,
                "role": "observer",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        membership = Membership.objects.get(household=household, user=new_user)
        assert membership.role == "observer"
