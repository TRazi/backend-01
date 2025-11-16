"""
Tests for reports APIs (apps/reports/apis.py).
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from datetime import datetime

from households.models import Household
from reports.services import ReportAccessError

User = get_user_model()


@pytest.mark.django_db
class TestSpendingReportApi:
    """Test SpendingReportApi view."""

    def test_spending_report_with_required_params(self):
        """Test generating spending report with required parameters."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        with patch("reports.apis.generate_spending_report") as mock_report:
            mock_report.return_value = {"total": 500, "by_category": []}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                "/api/v1/reports/spending/",
                {
                    "from_date": "2025-01-01T00:00:00Z",
                    "to_date": "2025-01-31T23:59:59Z",
                    "household_id": household.id,
                },
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data == {"total": 500, "by_category": []}
            mock_report.assert_called_once()

    def test_spending_report_with_household_header(self):
        """Test spending report with X-Household-ID header."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        with patch("reports.apis.generate_spending_report") as mock_report:
            mock_report.return_value = {"total": 500}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                "/api/v1/reports/spending/",
                {
                    "from_date": "2025-01-01T00:00:00Z",
                    "to_date": "2025-01-31T23:59:59Z",
                },
                HTTP_X_HOUSEHOLD_ID=str(household.id),
            )

            assert response.status_code == status.HTTP_200_OK

    def test_spending_report_with_category_filter(self):
        """Test spending report with category filter."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        with patch("reports.apis.generate_spending_report") as mock_report:
            mock_report.return_value = {"total": 200}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                "/api/v1/reports/spending/",
                {
                    "from_date": "2025-01-01T00:00:00Z",
                    "to_date": "2025-01-31T23:59:59Z",
                    "household_id": household.id,
                    "category_id": 5,
                },
            )

            assert response.status_code == status.HTTP_200_OK
            call_kwargs = mock_report.call_args.kwargs
            assert call_kwargs["category_id"] == 5

    def test_spending_report_missing_from_date(self):
        """Test spending report fails without from_date."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {"to_date": "2025-01-31T23:59:59Z", "household_id": 1},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "from_date and to_date" in response.data["detail"]

    def test_spending_report_missing_to_date(self):
        """Test spending report fails without to_date."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {"from_date": "2025-01-01T00:00:00Z", "household_id": 1},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "from_date and to_date" in response.data["detail"]

    def test_spending_report_invalid_from_date(self):
        """Test spending report fails with invalid from_date."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {
                "from_date": "invalid-date",
                "to_date": "2025-01-31T23:59:59Z",
                "household_id": 1,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ISO-8601" in response.data["detail"]

    def test_spending_report_invalid_to_date(self):
        """Test spending report fails with invalid to_date."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {
                "from_date": "2025-01-01T00:00:00Z",
                "to_date": "invalid-date",
                "household_id": 1,
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "ISO-8601" in response.data["detail"]

    def test_spending_report_missing_household_id(self):
        """Test spending report fails without household_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {
                "from_date": "2025-01-01T00:00:00Z",
                "to_date": "2025-01-31T23:59:59Z",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "household_id" in response.data["detail"]

    def test_spending_report_invalid_household_id(self):
        """Test spending report fails with invalid household_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {
                "from_date": "2025-01-01T00:00:00Z",
                "to_date": "2025-01-31T23:59:59Z",
                "household_id": "invalid",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "integer" in response.data["detail"]

    def test_spending_report_invalid_category_id(self):
        """Test spending report fails with invalid category_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(
            "/api/v1/reports/spending/",
            {
                "from_date": "2025-01-01T00:00:00Z",
                "to_date": "2025-01-31T23:59:59Z",
                "household_id": 1,
                "category_id": "invalid",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "category_id" in response.data["detail"]

    def test_spending_report_access_error(self):
        """Test spending report returns 404 on ReportAccessError."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        with patch("reports.apis.generate_spending_report") as mock_report:
            mock_report.side_effect = ReportAccessError("Access denied")

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                "/api/v1/reports/spending/",
                {
                    "from_date": "2025-01-01T00:00:00Z",
                    "to_date": "2025-01-31T23:59:59Z",
                    "household_id": 999,
                },
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data["detail"] == "Access denied"

    def test_spending_report_unauthenticated(self):
        """Test spending report requires authentication."""
        client = APIClient()
        response = client.get(
            "/api/v1/reports/spending/",
            {
                "from_date": "2025-01-01T00:00:00Z",
                "to_date": "2025-01-31T23:59:59Z",
                "household_id": 1,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestHouseholdExportApi:
    """Test HouseholdExportApi view."""

    def test_household_export_with_household_id_param(self):
        """Test exporting household data with household_id parameter."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        with patch("reports.apis.export_household_snapshot") as mock_export:
            mock_export.return_value = {"accounts": [], "budgets": []}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                f"/api/v1/backups/export/?household_id={household.id}"
            )

            assert response.status_code == status.HTTP_200_OK
            assert response.data == {"accounts": [], "budgets": []}
            mock_export.assert_called_once_with(user=user, household_id=household.id)

    def test_household_export_with_household_header(self):
        """Test household export with X-Household-ID header."""
        user = User.objects.create_user(email="test@example.com", password="pass123")
        household = Household.objects.create(name="Test Household")

        with patch("reports.apis.export_household_snapshot") as mock_export:
            mock_export.return_value = {"data": "exported"}

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get(
                "/api/v1/backups/export/",
                HTTP_X_HOUSEHOLD_ID=str(household.id),
            )

            assert response.status_code == status.HTTP_200_OK

    def test_household_export_missing_household_id(self):
        """Test household export fails without household_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/backups/export/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "household_id" in response.data["detail"]

    def test_household_export_invalid_household_id(self):
        """Test household export fails with invalid household_id."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/backups/export/?household_id=invalid")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "integer" in response.data["detail"]

    def test_household_export_access_error(self):
        """Test household export returns 404 on ReportAccessError."""
        user = User.objects.create_user(email="test@example.com", password="pass123")

        with patch("reports.apis.export_household_snapshot") as mock_export:
            mock_export.side_effect = ReportAccessError("Access denied")

            client = APIClient()
            client.force_authenticate(user=user)
            response = client.get("/api/v1/backups/export/?household_id=999")

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data["detail"] == "Access denied"

    def test_household_export_unauthenticated(self):
        """Test household export requires authentication."""
        client = APIClient()
        response = client.get("/api/v1/backups/export/?household_id=1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
