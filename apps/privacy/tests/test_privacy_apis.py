"""
Tests for privacy APIs (apps/privacy/apis.py).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock

from apps.households.models import Household, Membership
from apps.privacy.services import HouseholdAccessError

User = get_user_model()


@pytest.mark.django_db
class TestDataExportApi:
    """Test DataExportApi view."""

    def test_export_data_with_household_id_param(self):
        """Test exporting data with household_id query parameter."""
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

        with patch("privacy.apis.export_user_data") as mock_export:
            mock_export.return_value = {"data": "exported"}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                f"/api/v1/privacy/data-export/?household_id={household.id}"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data == {"data": "exported"}
            mock_export.assert_called_once_with(user=user, household_id=household.id)

    def test_export_data_with_household_id_header(self):
        """Test exporting data with X-Household-ID header."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        with patch("privacy.apis.export_user_data") as mock_export:
            mock_export.return_value = {"data": "exported"}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                "/api/v1/privacy/data-export/",
                HTTP_X_HOUSEHOLD_ID=str(household.id),
            )

            assert response.status_code == status.HTTP_200_OK
            mock_export.assert_called_once_with(user=user, household_id=household.id)

    def test_export_data_missing_household_id(self):
        """Test export fails without household_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/privacy/data-export/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "household_id" in response.data["detail"]

    def test_export_data_invalid_household_id(self):
        """Test export fails with invalid household_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/privacy/data-export/?household_id=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "integer" in response.data["detail"]

    def test_export_data_household_access_error(self):
        """Test export returns 404 on HouseholdAccessError."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        with patch("privacy.apis.export_user_data") as mock_export:
            mock_export.side_effect = HouseholdAccessError("Access denied")

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get("/api/v1/privacy/data-export/?household_id=999")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data["detail"] == "Access denied"

    def test_export_data_unauthenticated(self):
        """Test export requires authentication."""
        client = APIClient()
        response = client.get("/api/v1/privacy/data-export/?household_id=1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestDataDeletionRequestApi:
    """Test DataDeletionRequestApi view."""

    def test_request_deletion(self):
        """Test requesting data deletion."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        with patch("privacy.apis.request_data_deletion") as mock_request:
            mock_request.return_value = {"status": "requested"}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.post("/api/v1/privacy/delete-request/")

            assert response.status_code == status.HTTP_202_ACCEPTED
            assert response.data == {"status": "requested"}
            mock_request.assert_called_once_with(user=user)

    def test_request_deletion_unauthenticated(self):
        """Test deletion request requires authentication."""
        client = APIClient()
        response = client.post("/api/v1/privacy/delete-request/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_check_deletion_status(self):
        """Test checking deletion status."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        with patch("privacy.apis.get_data_deletion_status") as mock_status:
            mock_status.return_value = {"status": "pending"}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get("/api/v1/privacy/delete-request/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data == {"status": "pending"}
            mock_status.assert_called_once_with(user=user)

    def test_check_deletion_status_unauthenticated(self):
        """Test checking deletion status requires authentication."""
        client = APIClient()
        response = client.get("/api/v1/privacy/delete-request/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPrivacyInfoApi:
    """Test PrivacyInfoApi view."""

    def test_get_privacy_info_unauthenticated(self):
        """Test privacy info is publicly accessible."""
        client = APIClient()
        response = client.get("/api/v1/privacy/info/")

        assert response.status_code == status.HTTP_200_OK
        assert "product" in response.data
        assert response.data["product"] == "Kinwise"
        assert "jurisdiction" in response.data
        assert "data_subject_rights" in response.data
        assert "contact_email" in response.data
        assert "last_updated" in response.data

    def test_get_privacy_info_authenticated(self):
        """Test privacy info accessible when authenticated."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/privacy/info/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["product"] == "Kinwise"

    def test_privacy_info_contains_required_fields(self):
        """Test privacy info contains all required fields."""
        client = APIClient()
        response = client.get("/api/v1/privacy/info/")

        assert response.status_code == status.HTTP_200_OK
        assert "NZ Privacy Act 2020" in response.data["jurisdiction"]
        assert len(response.data["data_subject_rights"]) > 0
        assert "privacy@kinwise.co.nz" == response.data["contact_email"]
