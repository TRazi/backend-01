"""
Tests for Category ViewSet API endpoints.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.households.models import Household
from apps.categories.models import Category


@pytest.mark.django_db
class TestCategoryViewSetList:
    """Test category list endpoint."""

    def test_list_categories_authenticated(self):
        """Authenticated user can list their household's categories."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/categories/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(c["name"] == "Groceries" for c in response.data)

    def test_list_categories_unauthenticated(self):
        """Unauthenticated users cannot list categories."""
        client = APIClient()
        response = client.get("/api/v1/categories/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_list_categories_household_isolation(self):
        """Users only see categories from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        Category.objects.create(
            household=household1, name="Family 1 Cat", category_type="expense"
        )
        Category.objects.create(
            household=household2, name="Family 2 Cat", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/categories/")

        assert response.status_code == status.HTTP_200_OK
        names = [c["name"] for c in response.data]
        assert "Family 1 Cat" in names
        assert "Family 2 Cat" not in names

    def test_filter_by_category_type(self):
        """Can filter categories by type."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        Category.objects.create(
            household=household, name="Salary", category_type="income"
        )
        Category.objects.create(
            household=household, name="Food", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/categories/?category_type=income")

        assert response.status_code == status.HTTP_200_OK
        assert all(c["category_type"] == "income" for c in response.data)

    def test_filter_by_active_status(self):
        """Can filter categories by active status."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        Category.objects.create(
            household=household, name="Active", category_type="expense", is_active=True
        )
        Category.objects.create(
            household=household,
            name="Inactive",
            category_type="expense",
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/categories/?active=true")

        assert response.status_code == status.HTTP_200_OK
        names = [c["name"] for c in response.data]
        assert "Active" in names
        assert "Inactive" not in names

    def test_filter_by_deleted_status(self):
        """Can filter categories by deleted status."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        Category.objects.create(
            household=household,
            name="Normal",
            category_type="expense",
            is_deleted=False,
        )
        Category.objects.create(
            household=household,
            name="Deleted",
            category_type="expense",
            is_deleted=True,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/categories/?deleted=true")

        assert response.status_code == status.HTTP_200_OK
        names = [c["name"] for c in response.data]
        assert "Deleted" in names
        assert "Normal" not in names


@pytest.mark.django_db
class TestCategoryViewSetCreate:
    """Test category creation endpoint."""

    def test_create_category_valid(self):
        """Can create a valid category."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"name": "Entertainment", "category_type": "expense", "icon": "🎬"}

        response = client.post("/api/v1/categories/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Entertainment"
        # Verify category was created for the user's household
        created_category = Category.objects.filter(
            name="Entertainment", household=household
        )
        assert created_category.exists()


@pytest.mark.django_db
class TestCategoryViewSetUpdate:
    """Test category update endpoint."""

    def test_update_category_valid(self):
        """Can update a category."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        category = Category.objects.create(
            household=household, name="Old Name", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"name": "New Name"}
        response = client.patch(f"/api/v1/categories/{category.id}/", data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "New Name"

    def test_update_system_category_prevented(self):
        """Cannot update system categories."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        category = Category.objects.create(
            household=household,
            name="System Category",
            category_type="expense",
            is_system=True,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {"name": "New Name"}
        response = client.patch(f"/api/v1/categories/{category.id}/", data)

        # Should be rejected by serializer validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestCategoryViewSetDelete:
    """Test category deletion (soft delete) endpoint."""

    def test_delete_category_soft_deletes(self):
        """Delete performs soft delete."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        category = Category.objects.create(
            household=household, name="To Delete", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/categories/{category.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Category still exists but is soft deleted
        category.refresh_from_db()
        assert category.is_deleted is True
        assert category.is_active is False

    def test_delete_system_category_prevented(self):
        """Cannot delete system categories."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        category = Category.objects.create(
            household=household,
            name="System Category",
            category_type="expense",
            is_system=True,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/categories/{category.id}/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "System categories cannot be deleted" in str(response.data)


@pytest.mark.django_db
class TestCategoryRestoreAction:
    """Test restore custom action."""

    def test_restore_deleted_category(self):
        """Can restore a soft-deleted category."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        category = Category.objects.create(
            household=household,
            name="Deleted Category",
            category_type="expense",
            is_deleted=True,
            is_active=False,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f"/api/v1/categories/{category.id}/restore/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_deleted"] is False
        assert response.data["is_active"] is True

        category.refresh_from_db()
        assert category.is_deleted is False
        assert category.is_active is True

    def test_restore_system_category_prevented(self):
        """Cannot restore system categories."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        category = Category.objects.create(
            household=household,
            name="System Category",
            category_type="expense",
            is_system=True,
            is_deleted=True,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(f"/api/v1/categories/{category.id}/restore/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "System categories cannot be restored" in str(response.data)


@pytest.mark.django_db
class TestCategoryViewSetStaffAccess:
    """Test staff user privileges."""

    def test_staff_sees_all_categories(self):
        """Staff users can see all categories across households."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        staff_user = User.objects.create_user(
            email="staff@test.com",
            password="pass123",
            first_name="Staff",
            household=household1,
            is_staff=True,
        )

        Category.objects.create(
            household=household1, name="Cat 1", category_type="expense"
        )
        Category.objects.create(
            household=household2, name="Cat 2", category_type="expense"
        )

        client = APIClient()
        client.force_authenticate(user=staff_user)
        response = client.get("/api/v1/categories/")

        assert response.status_code == status.HTTP_200_OK
        names = [c["name"] for c in response.data]
        assert "Cat 1" in names
        assert "Cat 2" in names
