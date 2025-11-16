"""
Tests for user API views and viewsets.
Tests UserViewSet only (users app functionality).
Privacy API tests (DataExportApi, etc.) belong in privacy app tests.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestUserViewSet:
    """Test UserViewSet."""

    def test_list_users_as_regular_user(self):
        """Test regular user can only see their own user."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        User.objects.create_user(email="other@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get("/api/v1/users/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["email"] == "test@example.com"

    def test_list_users_as_staff(self):
        """Test staff user can see all users."""
        staff_user = User.objects.create_user(
            email="staff@example.com", password="pass123", is_staff=True
        )
        User.objects.create_user(email="user1@example.com", password="pass123")
        User.objects.create_user(email="user2@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.get("/api/v1/users/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 3  # At least staff + 2 users

    def test_retrieve_user_as_owner(self):
        """Test user can retrieve their own details."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/users/{user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "test@example.com"
        assert response.data["first_name"] == "John"
        assert response.data["last_name"] == "Doe"

    def test_retrieve_other_user_as_regular_user(self):
        """Test regular user cannot retrieve other users."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        other_user = User.objects.create_user(
            email="other@example.com", password="pass123"
        )

        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(f"/api/v1/users/{other_user.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_other_user_as_staff(self):
        """Test staff user can retrieve other users."""
        staff_user = User.objects.create_user(
            email="staff@example.com", password="pass123", is_staff=True
        )
        other_user = User.objects.create_user(
            email="other@example.com", password="pass123"
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)

        response = client.get(f"/api/v1/users/{other_user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "other@example.com"

    def test_unauthenticated_access_forbidden(self):
        """Test unauthenticated access is forbidden."""
        client = APIClient()
        response = client.get("/api/v1/users/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]
