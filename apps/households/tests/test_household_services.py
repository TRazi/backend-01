"""
Tests for households service functions.
"""

import pytest

from apps.households.models import Household, Membership
from apps.households.services import (
    membership_create,
    membership_set_primary,
    membership_deactivate,
)
from apps.users.models import User
from django.core.exceptions import ValidationError


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_create():
    """Test creating a new membership."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="admin",
        is_primary=False,
    )

    assert membership is not None
    assert membership.user == user
    assert membership.household == household
    assert membership.role == "admin"
    assert membership.is_primary is False


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_create_as_primary():
    """Test creating a new membership as primary."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="parent",
        is_primary=True,
    )

    assert membership.is_primary is True

    # User should be synced
    user.refresh_from_db()
    assert user.household == household


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_create_duplicate_raises_error():
    """Test that creating duplicate membership raises error."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="parent",
    )

    # Try to create duplicate
    with pytest.raises(ValidationError, match="already a member"):
        membership_create(
            user=user,
            household=household,
            membership_type="fw",
            role="parent",
        )


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_set_primary():
    """Test setting a membership as primary."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household1 = Household.objects.create(
        name="Household 1",
        household_type="fam",
        budget_cycle="m",
    )
    household2 = Household.objects.create(
        name="Household 2",
        household_type="fam",
        budget_cycle="m",
    )

    membership1 = membership_create(
        user=user,
        household=household1,
        membership_type="fw",
        role="admin",
        is_primary=True,
    )

    membership2 = membership_create(
        user=user,
        household=household2,
        membership_type="sw",
        role="parent",
        is_primary=False,
    )

    # Set membership2 as primary
    membership_set_primary(membership=membership2)

    # membership2 should be primary
    membership2.refresh_from_db()
    assert membership2.is_primary is True

    # membership1 should no longer be primary
    membership1.refresh_from_db()
    assert membership1.is_primary is False

    # User's household should be synced to membership2
    user.refresh_from_db()
    assert user.household == household2
    assert user.role == "parent"


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_set_primary_inactive_raises_error():
    """Test that setting inactive membership as primary raises error."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="admin",
        is_primary=True,
    )

    # Deactivate and try to set as primary
    membership_deactivate(membership=membership, status="cancelled")

    with pytest.raises(ValidationError, match="Only active memberships"):
        membership_set_primary(membership=membership)


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_deactivate():
    """Test deactivating a membership."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="admin",
        is_primary=True,
    )

    # Deactivate
    deactivated = membership_deactivate(membership=membership, status="cancelled")

    assert deactivated.status == "cancelled"
    assert deactivated.is_primary is False
    assert deactivated.ended_at is not None


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_deactivate_switches_primary():
    """Test that deactivating primary membership switches to another."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household1 = Household.objects.create(
        name="Household 1",
        household_type="fam",
        budget_cycle="m",
    )
    household2 = Household.objects.create(
        name="Household 2",
        household_type="fam",
        budget_cycle="m",
    )

    membership1 = membership_create(
        user=user,
        household=household1,
        membership_type="fw",
        role="admin",
        is_primary=True,
    )

    membership2 = membership_create(
        user=user,
        household=household2,
        membership_type="sw",
        role="parent",
        is_primary=False,
    )

    # Deactivate primary membership
    membership_deactivate(membership=membership1, status="cancelled")

    # membership2 should become primary
    membership2.refresh_from_db()
    assert membership2.is_primary is True

    # User should be synced to membership2
    user.refresh_from_db()
    assert user.household == household2


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_deactivate_last_membership_clears_user_household():
    """Test that deactivating last membership clears user's household."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="admin",
        is_primary=True,
    )

    # Deactivate the only membership
    membership_deactivate(membership=membership, status="cancelled")

    # User should have no household
    user.refresh_from_db()
    assert user.household is None
    assert user.role == "observer"


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_create_with_different_membership_types():
    """Test creating memberships with various membership types."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    # Test shared wallet
    membership_sw = membership_create(
        user=user,
        household=household,
        membership_type="sw",
        role="parent",
        is_primary=True,
    )
    assert membership_sw.membership_type == "sw"

    # Test family wallet
    user2 = User.objects.create_user(
        email="test2@example.com",
        password="testpass123",
    )
    membership_fw = membership_create(
        user=user2,
        household=household,
        membership_type="fw",
        role="child",
        is_primary=True,
    )
    assert membership_fw.membership_type == "fw"


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_set_primary_updates_user_role():
    """Test that setting primary membership updates user's role."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="parent",
        is_primary=False,
    )

    # Set as primary
    membership_set_primary(membership=membership)

    # Check user role is synced
    user.refresh_from_db()
    assert user.role == "parent"


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_deactivate_with_different_statuses():
    """Test deactivating memberships with different statuses."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    # Test expired status
    membership1 = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="admin",
        is_primary=False,
    )
    result = membership_deactivate(membership=membership1, status="expired")
    assert result.ended_at is not None

    # Test cancelled status
    user2 = User.objects.create_user(
        email="test2@example.com",
        password="testpass123",
    )
    membership2 = membership_create(
        user=user2,
        household=household,
        membership_type="fw",
        role="parent",
        is_primary=False,
    )
    result = membership_deactivate(membership=membership2, status="cancelled")
    assert result.ended_at is not None


@pytest.mark.django_db
@pytest.mark.unit
def test_membership_deactivate_invalid_status_raises_error():
    """Test that invalid deactivation status raises error."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    membership = membership_create(
        user=user,
        household=household,
        membership_type="fw",
        role="admin",
    )

    # Try invalid status
    with pytest.raises(ValidationError, match="Invalid deactivation status"):
        membership_deactivate(membership=membership, status="invalid_status")
