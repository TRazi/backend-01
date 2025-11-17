"""Tests for category permissions."""

import pytest
from unittest.mock import Mock
from django.contrib.auth import get_user_model

from apps.categories.models import Category
from apps.categories.permissions import IsCategoryHouseholdMember
from apps.households.models import Household

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestIsCategoryHouseholdMember:
    """Test IsCategoryHouseholdMember permission."""

    def test_unauthenticated_user_denied(self):
        """Test unauthenticated users are denied."""
        permission = IsCategoryHouseholdMember()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        household = Household.objects.create(name="Test Household")
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )

        assert not permission.has_object_permission(request, None, category)

    def test_staff_user_allowed(self):
        """Test staff users are always allowed."""
        permission = IsCategoryHouseholdMember()
        user = User.objects.create_user(email="staff@test.com", password="test")
        user.is_staff = True
        user.save()

        request = Mock()
        request.user = user

        household = Household.objects.create(name="Test Household")
        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )

        assert permission.has_object_permission(request, None, category)

    def test_same_household_allowed(self):
        """Test users from same household are allowed."""
        permission = IsCategoryHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="test")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        category = Category.objects.create(
            household=household, name="Test Category", category_type="expense"
        )

        assert permission.has_object_permission(request, None, category)

    def test_different_household_denied(self):
        """Test users from different household are denied."""
        permission = IsCategoryHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        user = User.objects.create_user(email="user@test.com", password="test")
        user.household = household1
        user.save()

        request = Mock()
        request.user = user

        category = Category.objects.create(
            household=household2, name="Test Category", category_type="expense"
        )

        assert not permission.has_object_permission(request, None, category)
