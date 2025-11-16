"""
Integration tests for User ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status

from users.models import User


@pytest.mark.django_db
class TestUserViewSetList:
    """Test user list endpoint."""

    def test_list_users_authenticated_regular_user(self):
        """Regular users only see themselves."""
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
            first_name="User",
            last_name="One",
        )
        User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
            first_name="User",
            last_name="Two",
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/users/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["email"] == "user1@test.com"

    def test_list_users_staff_user(self):
        """Staff users see all users."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            first_name="Admin",
            is_staff=True,
        )
        User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
            first_name="User1",
        )
        User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
            first_name="User2",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/users/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        emails = [user["email"] for user in response.data]
        assert "admin@test.com" in emails
        assert "user1@test.com" in emails
        assert "user2@test.com" in emails

    def test_list_users_unauthenticated(self):
        """Unauthenticated users cannot access user list."""
        client = APIClient()
        response = client.get("/api/v1/users/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserViewSetRetrieve:
    """Test user retrieve endpoint."""

    def test_retrieve_own_user(self):
        """User can retrieve their own details."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/users/{user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "user@test.com"
        assert response.data["first_name"] == "Test"

    def test_retrieve_other_user_as_regular_user(self):
        """Regular users cannot retrieve other users."""
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
            first_name="User1",
        )
        user2 = User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
            first_name="User2",
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get(f"/api/v1/users/{user2.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_other_user_as_staff(self):
        """Staff users can retrieve any user."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        target_user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Target",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/users/{target_user.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "user@test.com"


@pytest.mark.django_db
class TestUserViewSetReadOnly:
    """Test that UserViewSet is read-only."""

    def test_create_user_not_allowed(self):
        """Creating users via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post(
            "/api/v1/users/",
            {
                "email": "new@test.com",
                "first_name": "New",
                "password": "testpass123",
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_user_not_allowed(self):
        """Updating users via ViewSet is not allowed."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Original",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.put(
            f"/api/v1/users/{user.id}/",
            {
                "email": "user@test.com",
                "first_name": "Updated",
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_user_not_allowed(self):
        """Deleting users via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.delete(f"/api/v1/users/{user.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
