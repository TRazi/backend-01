"""
Test suite for category serializers.
Tests validation logic and serialization behavior.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from categories.models import Category
from categories.serializers import (
    CategorySerializer,
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
)
from households.models import Household, Membership

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestCategorySerializer:
    """Test CategorySerializer behavior."""

    def test_serializer_includes_computed_fields(self):
        """Test that serializer includes computed fields from model."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        category = Category.objects.create(
            household=household,
            name="Groceries",
            category_type="expense",  # lowercase
            is_active=True,
        )

        serializer = CategorySerializer(category)

        assert "full_path" in serializer.data
        assert "transaction_count" in serializer.data
        assert "total_amount" in serializer.data
        assert "usage_stats" in serializer.data

    def test_serializer_read_only_fields(self):
        """Test that read-only fields are properly marked."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        category = Category.objects.create(
            household=household,
            name="Test Category",
            category_type="expense",  # lowercase
        )

        serializer = CategorySerializer(category)

        # Verify read-only fields are present in data
        assert serializer.data["household"] == household.id
        assert serializer.data["is_system"] is False
        assert "created_at" in serializer.data


@pytest.mark.django_db
@pytest.mark.unit
class TestCategoryCreateSerializer:
    """Test CategoryCreateSerializer behavior."""

    def test_create_sets_household_from_user(self):
        """Test that create() automatically sets household from request.user."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = CategoryCreateSerializer(
            data={
                "name": "Entertainment",
                "description": "Entertainment expenses",
                "category_type": "expense",  # lowercase
                "is_active": True,
            },
            context={"request": request},
        )

        # Serializer should be valid
        if not serializer.is_valid():
            print(f"Validation errors: {serializer.errors}")
        assert serializer.is_valid()
        category = serializer.save()

        assert category.household == household
        assert category.name == "Entertainment"
        assert category.is_system is False
        assert category.is_deleted is False

    def test_create_with_parent_category(self):
        """Test creating subcategory with parent."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        parent = Category.objects.create(
            household=household,
            name="Entertainment",
            category_type="expense",  # lowercase
        )

        request = Mock()
        request.user = user

        serializer = CategoryCreateSerializer(
            data={
                "name": "Movies",
                "category_type": "expense",  # lowercase
                "parent": parent.id,
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        category = serializer.save()

        assert category.parent == parent
        assert category.household == household


@pytest.mark.django_db
@pytest.mark.unit
class TestCategoryUpdateSerializer:
    """Test CategoryUpdateSerializer validation."""

    def test_validate_system_category_update(self):
        """Test validation fails when updating system category."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        system_category = Category.objects.create(
            household=household,
            name="System Category",
            category_type="expense",  # lowercase
            is_system=True,
        )

        serializer = CategoryUpdateSerializer(
            instance=system_category,
            data={"name": "Modified Name"},
            partial=True,
        )

        assert not serializer.is_valid()
        assert "System categories cannot be updated" in str(
            serializer.errors["non_field_errors"]
        )

    def test_update_non_system_category_succeeds(self):
        """Test that updating non-system category succeeds."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        category = Category.objects.create(
            household=household,
            name="Original Name",
            category_type="expense",  # lowercase
            is_system=False,
        )

        serializer = CategoryUpdateSerializer(
            instance=category,
            data={"name": "Updated Name", "description": "New description"},
            partial=True,
        )

        assert serializer.is_valid()
        updated_category = serializer.save()

        assert updated_category.name == "Updated Name"
        assert updated_category.description == "New description"

    def test_category_serializer_get_methods(self):
        """Test CategorySerializer get methods are called."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )

        serializer = CategorySerializer(category)

        # Test get methods are called
        assert (
            serializer.get_transaction_count(category)
            == category.get_transaction_count()
        )
        assert serializer.get_total_amount(category) == category.get_total_amount()
        assert serializer.get_usage_stats(category) == category.get_usage_stats()


@pytest.mark.django_db
@pytest.mark.unit
class TestCategorySerializerValidation:
    """Test Category serializer validation."""

    def test_system_category_cannot_be_updated(self):
        """Test that system categories cannot be updated."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        system_category = Category.objects.create(
            household=household,
            name="System Category",
            category_type="expense",
            is_system=True,
        )

        serializer = CategoryUpdateSerializer(
            instance=system_category,
            data={"name": "New Name"},
            partial=True,
        )

        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors

    def test_category_create_with_parent(self):
        """Test creating category with parent."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")
        user.household = household
        user.save()

        parent = Category.objects.create(
            household=household, name="Parent", category_type="expense"
        )

        from unittest.mock import Mock

        request = Mock()
        request.user = user

        serializer = CategoryCreateSerializer(
            data={
                "name": "Child Category",
                "category_type": "expense",
                "parent": parent.id,
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        child = serializer.save()
        assert child.parent == parent
        assert child.household == household
        assert child.is_system is False

    def test_category_serializer_computed_fields(self):
        """Test category serializer includes computed fields."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        Membership.objects.create(user=user, household=household, role="admin")

        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )

        serializer = CategorySerializer(category)

        assert "full_path" in serializer.data
        assert "transaction_count" in serializer.data
        assert "total_amount" in serializer.data
        assert "usage_stats" in serializer.data
