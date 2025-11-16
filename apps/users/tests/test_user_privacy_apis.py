"""
Additional tests for users APIs (apps/users/apis.py).
Supplements existing test_user_apis.py with tests for privacy-related views.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from households.models import Household

User = get_user_model()


@pytest.mark.django_db
class TestUserDataExportView:
    """Test UserDataExportView for Privacy Act compliance."""

    def test_export_user_data_authenticated(self):
        """Test authenticated user can export their data."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
            phone_number="+64212345678",
            email_verified=True,
            locale="en_NZ",
        )
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/users/me/data-export/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == user.id
        assert response.data["email"] == "test@example.com"
        assert response.data["first_name"] == "John"
        assert response.data["last_name"] == "Doe"
        assert response.data["phone_number"] == "+64212345678"
        assert response.data["email_verified"] is True
        assert response.data["locale"] == "en_NZ"
        assert response.data["household_id"] == household.id
        assert "created_at" in response.data
        assert "updated_at" in response.data

    def test_export_user_data_unauthenticated(self):
        """Test unauthenticated user cannot export data."""
        client = APIClient()
        response = client.get("/api/v1/users/me/data-export/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_export_user_data_without_household(self):
        """Test user data export works without household."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="Jane",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/users/me/data-export/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "test@example.com"
        assert response.data["household_id"] is None

    def test_export_user_data_includes_role(self):
        """Test user data export includes role."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            role="PARENT",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/users/me/data-export/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["role"] == "PARENT"


@pytest.mark.django_db
class TestCorrectionRequestView:
    """Test CorrectionRequestView for Privacy Act compliance."""

    def test_submit_correction_request(self):
        """Test authenticated user can submit correction request."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/users/me/correction-request/",
            {
                "field": "email",
                "current_value": "test@example.com",
                "requested_value": "newemail@example.com",
                "reason": "Email address changed",
            },
            format="json",
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "message" in response.data
        assert "submitted_data" in response.data
        assert response.data["submitted_data"]["field"] == "email"

    def test_submit_correction_request_unauthenticated(self):
        """Test unauthenticated user cannot submit correction request."""
        client = APIClient()
        response = client.post(
            "/api/v1/users/me/correction-request/",
            {"field": "email", "requested_value": "test@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_submit_correction_request_with_empty_data(self):
        """Test correction request accepts empty data."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/users/me/correction-request/", {}, format="json"
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["submitted_data"] == {}

    def test_submit_correction_request_with_complex_data(self):
        """Test correction request with complex nested data."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        request_data = {
            "fields": ["first_name", "last_name"],
            "current_values": {"first_name": "John", "last_name": "Doe"},
            "requested_values": {"first_name": "Jane", "last_name": "Smith"},
            "reason": "Legal name change",
            "documents": ["marriage_certificate.pdf"],
        }

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/users/me/correction-request/", request_data, format="json"
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["submitted_data"]["reason"] == "Legal name change"


@pytest.mark.django_db
class TestUserDeletionRequestView:
    """Test UserDeletionRequestView for Privacy Act compliance."""

    def test_submit_deletion_request(self):
        """Test authenticated user can request account deletion."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", is_active=True
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/me/delete-request/")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "message" in response.data
        assert "deletion request" in response.data["message"]

        # Verify user is marked as inactive
        user.refresh_from_db()
        assert user.is_active is False

    def test_submit_deletion_request_unauthenticated(self):
        """Test unauthenticated user cannot request deletion."""
        client = APIClient()
        response = client.post("/api/v1/users/me/delete-request/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deletion_request_marks_user_inactive(self):
        """Test deletion request properly marks user as inactive."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", is_active=True
        )

        assert user.is_active is True

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/me/delete-request/")

        assert response.status_code == status.HTTP_202_ACCEPTED

        user.refresh_from_db()
        assert user.is_active is False

    def test_deletion_request_idempotent(self):
        """Test deletion request can be called multiple times."""
        user = User.objects.create_user(
            email="test@example.com", password="pass123", is_active=True
        )

        client = APIClient()
        client.force_authenticate(user=user)

        # First request
        response1 = client.post("/api/v1/users/me/delete-request/")
        assert response1.status_code == status.HTTP_202_ACCEPTED

        # Second request
        response2 = client.post("/api/v1/users/me/delete-request/")
        assert response2.status_code == status.HTTP_202_ACCEPTED

        user.refresh_from_db()
        assert user.is_active is False

    def test_deletion_request_preserves_user_data(self):
        """Test deletion request doesn't delete user immediately."""
        user = User.objects.create_user(
            email="test@example.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post("/api/v1/users/me/delete-request/")

        assert response.status_code == status.HTTP_202_ACCEPTED

        # User still exists but is inactive
        user.refresh_from_db()
        assert user.email == "test@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.is_active is False
