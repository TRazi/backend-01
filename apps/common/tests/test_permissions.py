"""
Tests for bills, goals, lessons, organisations, and rewards app permissions.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.bills.permissions import IsBillHouseholdMember
from apps.goals.permissions import IsGoalHouseholdMember, IsGoalProgressHouseholdMember
from apps.lessons.permissions import IsAuthenticatedReadOnly
from apps.organisations.permissions import IsAdminOnly
from apps.rewards.permissions import IsRewardOwnerOrAdmin
from apps.bills.models import Bill
from apps.goals.models import Goal, GoalProgress
from apps.households.models import Household
from apps.rewards.models import Reward

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestIsBillHouseholdMember:
    """Test IsBillHouseholdMember permission class."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        permission = IsBillHouseholdMember()
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="Electric Bill",
            amount=150.00,
            due_date=date(2025, 12, 1),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert permission.has_object_permission(request, None, bill) is False

    def test_staff_user_allowed(self):
        """Staff users should have full access."""
        permission = IsBillHouseholdMember()
        household = Household.objects.create(name="Test Household")
        bill = Bill.objects.create(
            household=household,
            name="Electric Bill",
            amount=150.00,
            due_date=date(2025, 12, 1),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, bill) is True

    def test_same_household_allowed(self):
        """Users in the same household should have access."""
        permission = IsBillHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household
        user.save()

        bill = Bill.objects.create(
            household=household,
            name="Electric Bill",
            amount=150.00,
            due_date=date(2025, 12, 1),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, bill) is True

    def test_different_household_denied(self):
        """Users in different households should be denied access."""
        permission = IsBillHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household1
        user.save()

        bill = Bill.objects.create(
            household=household2,
            name="Electric Bill",
            amount=150.00,
            due_date=date(2025, 12, 1),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, bill) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestIsGoalHouseholdMember:
    """Test IsGoalHouseholdMember permission class."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        permission = IsGoalHouseholdMember()
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert permission.has_object_permission(request, None, goal) is False

    def test_staff_user_allowed(self):
        """Staff users should have full access."""
        permission = IsGoalHouseholdMember()
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, goal) is True

    def test_same_household_allowed(self):
        """Users in the same household should have access."""
        permission = IsGoalHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household
        user.save()

        goal = Goal.objects.create(
            household=household,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, goal) is True

    def test_different_household_denied(self):
        """Users in different households should be denied access."""
        permission = IsGoalHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household1
        user.save()

        goal = Goal.objects.create(
            household=household2,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, goal) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestIsGoalProgressHouseholdMember:
    """Test IsGoalProgressHouseholdMember permission class."""

    def test_staff_user_allowed(self):
        """Staff users should have full access."""
        permission = IsGoalProgressHouseholdMember()
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )
        progress = GoalProgress.objects.create(goal=goal, amount_added=100.00)

        request = Mock()
        request.user = Mock()
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, progress) is True

    def test_same_household_allowed(self):
        """Users in the same household should have access."""
        permission = IsGoalProgressHouseholdMember()
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household
        user.save()

        goal = Goal.objects.create(
            household=household,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )
        progress = GoalProgress.objects.create(goal=goal, amount_added=100.00)

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, progress) is True

    def test_different_household_denied(self):
        """Users in different households should be denied access."""
        permission = IsGoalProgressHouseholdMember()
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        user.household = household1
        user.save()

        goal = Goal.objects.create(
            household=household2,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )
        progress = GoalProgress.objects.create(goal=goal, amount_added=100.00)

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, progress) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestIsAuthenticatedReadOnly:
    """Test IsAuthenticatedReadOnly permission class for lessons."""

    def test_unauthenticated_user_denied_has_permission(self):
        """Unauthenticated users should be denied at view level."""
        permission = IsAuthenticatedReadOnly()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert permission.has_permission(request, None) is False

    def test_authenticated_user_allowed_has_permission(self):
        """Authenticated users should have access at view level."""
        permission = IsAuthenticatedReadOnly()
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        request = Mock()
        request.user = user

        assert permission.has_permission(request, None) is True

    def test_authenticated_user_allowed_has_object_permission(self):
        """Authenticated users should have access at object level."""
        permission = IsAuthenticatedReadOnly()
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, Mock()) is True


@pytest.mark.django_db
@pytest.mark.unit
class TestIsAdminOnly:
    """Test IsAdminOnly permission class for organisations."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied."""
        permission = IsAdminOnly()
        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert permission.has_permission(request, None) is False

    def test_authenticated_non_staff_denied(self):
        """Authenticated non-staff users should be denied."""
        permission = IsAdminOnly()
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        request = Mock()
        request.user = user

        assert permission.has_permission(request, None) is False

    def test_staff_user_allowed(self):
        """Staff users should have full access."""
        permission = IsAdminOnly()
        user = User.objects.create_user(email="admin@test.com", password="testpass123")
        user.is_staff = True
        user.save()
        request = Mock()
        request.user = user

        assert permission.has_permission(request, None) is True
        assert permission.has_object_permission(request, None, Mock()) is True


@pytest.mark.django_db
@pytest.mark.unit
class TestIsRewardOwnerOrAdmin:
    """Test IsRewardOwnerOrAdmin permission class."""

    def test_unauthenticated_user_denied(self):
        """Unauthenticated users should be denied access."""
        permission = IsRewardOwnerOrAdmin()
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        reward = Reward.objects.create(
            user=user,
            title="Achievement Unlocked",
            points=100,
            earned_on=timezone.now(),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = False

        assert permission.has_object_permission(request, None, reward) is False

    def test_staff_user_allowed(self):
        """Staff users should have full access."""
        permission = IsRewardOwnerOrAdmin()
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        reward = Reward.objects.create(
            user=user,
            title="Achievement Unlocked",
            points=100,
            earned_on=timezone.now(),
        )

        request = Mock()
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_staff = True

        assert permission.has_object_permission(request, None, reward) is True

    def test_reward_owner_allowed(self):
        """Reward owners should have access to their own rewards."""
        permission = IsRewardOwnerOrAdmin()
        user = User.objects.create_user(email="user@test.com", password="testpass123")
        reward = Reward.objects.create(
            user=user,
            title="Achievement Unlocked",
            points=100,
            earned_on=timezone.now(),
        )

        request = Mock()
        request.user = user

        assert permission.has_object_permission(request, None, reward) is True

    def test_different_user_denied(self):
        """Users should not access other users' rewards."""
        permission = IsRewardOwnerOrAdmin()
        user1 = User.objects.create_user(email="user1@test.com", password="testpass123")
        user2 = User.objects.create_user(email="user2@test.com", password="testpass123")
        reward = Reward.objects.create(
            user=user1,
            title="Achievement Unlocked",
            points=100,
            earned_on=timezone.now(),
        )

        request = Mock()
        request.user = user2

        assert permission.has_object_permission(request, None, reward) is False
