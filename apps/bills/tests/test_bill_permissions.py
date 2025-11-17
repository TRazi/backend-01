"""
Tests for Bill permissions.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.users.models import User
from apps.households.models import Household
from apps.bills.models import Bill
from apps.bills.permissions import IsBillHouseholdMember


@pytest.mark.django_db
class TestIsBillHouseholdMember:
    """Test IsBillHouseholdMember permission."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users are denied access."""
        from django.contrib.auth.models import AnonymousUser

        household = Household.objects.create(name="Test Family")
        bill = Bill.objects.create(
            household=household, name="Bill", amount=100, due_date=timezone.now().date()
        )

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = AnonymousUser()

        permission = IsBillHouseholdMember()
        has_perm = permission.has_object_permission(request, None, bill)

        assert has_perm is False

    def test_staff_user_allowed(self):
        """Staff users can access any bill."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        staff_user = User.objects.create_user(
            email="staff@test.com",
            password="pass123",
            first_name="Staff",
            household=household1,
            is_staff=True,
        )

        bill = Bill.objects.create(
            household=household2,
            name="Bill",
            amount=100,
            due_date=timezone.now().date(),
        )

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = staff_user

        permission = IsBillHouseholdMember()
        has_perm = permission.has_object_permission(request, None, bill)

        assert has_perm is True

    def test_same_household_allowed(self):
        """User can access bills from their household."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        bill = Bill.objects.create(
            household=household, name="Bill", amount=100, due_date=timezone.now().date()
        )

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user

        permission = IsBillHouseholdMember()
        has_perm = permission.has_object_permission(request, None, bill)

        assert has_perm is True

    def test_different_household_denied(self):
        """User cannot access bills from different household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household1,
        )

        bill = Bill.objects.create(
            household=household2,
            name="Bill",
            amount=100,
            due_date=timezone.now().date(),
        )

        factory = APIRequestFactory()
        request = factory.get("/")
        request.user = user

        permission = IsBillHouseholdMember()
        has_perm = permission.has_object_permission(request, None, bill)

        assert has_perm is False
