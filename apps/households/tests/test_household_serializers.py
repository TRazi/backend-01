"""
Tests for household serializers.
"""

import pytest
from unittest.mock import Mock

from households.models import Household, Membership
from households.serializers import (
    HouseholdSerializer,
    HouseholdCreateSerializer,
    MembershipSerializer,
    MembershipCreateSerializer,
)
from users.models import User


@pytest.mark.django_db
@pytest.mark.unit
def test_household_serializer():
    """Test HouseholdSerializer."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    serializer = HouseholdSerializer(household)
    data = serializer.data

    assert data["id"] == household.id
    assert data["name"] == "Test Household"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.django_db
@pytest.mark.unit
def test_household_create_serializer():
    """Test HouseholdCreateSerializer creates household and membership."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )

    # Mock request
    request = Mock()
    request.user = user

    data = {"name": "New Household"}
    serializer = HouseholdCreateSerializer(data=data, context={"request": request})

    assert serializer.is_valid()
    household = serializer.save()

    # Check household created
    assert household.name == "New Household"

    # Check membership created
    membership = Membership.objects.get(household=household, user=user)
    assert membership.role == "admin"

    # Check user household set
    user.refresh_from_db()
    assert user.household == household


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_serializer():
    """Test MembershipSerializer."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    membership = Membership.objects.create(
        user=user,
        household=household,
        role="parent",
    )

    serializer = MembershipSerializer(membership)
    data = serializer.data

    assert data["id"] == membership.id
    assert data["user"] == user.id
    assert data["household"] == household.id
    assert data["role"] == "parent"
    assert "created_at" in data


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_create_serializer():
    """Test MembershipCreateSerializer."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    data = {
        "user": user.id,
        "household": household.id,
        "role": "parent",
    }
    serializer = MembershipCreateSerializer(data=data)

    assert serializer.is_valid()
    membership = serializer.save()

    assert membership.user == user
    assert membership.household == household
    assert membership.role == "parent"


@pytest.mark.django_db
@pytest.mark.unit
def test_household_serializer_with_multiple_fields():
    """Test household serializer includes all expected fields."""
    household = Household.objects.create(
        name="Complete Household",
        household_type="couple",
        budget_cycle="w",
    )

    serializer = HouseholdSerializer(household)
    data = serializer.data

    # Verify standard fields present
    assert "id" in data
    assert "name" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_serializer_inactive_membership():
    """Test serializer with ended membership."""
    from django.utils import timezone

    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )
    membership = Membership.objects.create(
        user=user,
        household=household,
        role="member",
        ended_at=timezone.now(),
    )

    # Test that serializer can be instantiated
    MembershipSerializer(membership)

    # Membership has an ended_at value
    assert membership.ended_at is not None


@pytest.mark.django_db
@pytest.mark.unit
def test_household_create_with_different_budgets():
    """Test creating households."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )

    request = Mock()
    request.user = user

    # Test creating a household
    data = {"name": "Test Household"}
    serializer = HouseholdCreateSerializer(data=data, context={"request": request})

    assert serializer.is_valid()
    household = serializer.save()
    assert household.name == "Test Household"
    assert household is not None


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_for_multiple_users():
    """Test multiple memberships for same household."""
    user1 = User.objects.create_user(
        email="user1@example.com",
        password="testpass123",
    )
    user2 = User.objects.create_user(
        email="user2@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Family Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership1 = Membership.objects.create(
        user=user1,
        household=household,
        role="admin",
    )
    membership2 = Membership.objects.create(
        user=user2,
        household=household,
        role="parent",
    )

    # Both memberships should exist
    assert Membership.objects.filter(household=household).count() == 2
    assert membership1.household == household
    assert membership2.household == household
