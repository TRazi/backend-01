"""
Tests for Goal ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

from apps.users.models import User
from apps.households.models import Household
from apps.goals.models import Goal, GoalProgress


@pytest.mark.django_db
class TestGoalViewSetList:
    """Test goal list endpoint."""

    def test_list_goals_authenticated(self):
        """Authenticated user can list their household's goals."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )
        Goal.objects.create(
            household=household,
            name="Vacation Fund",
            target_amount=Decimal("5000.00"),
            due_date=(timezone.now() + timedelta(days=365)).date(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/goals/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Vacation Fund"

    def test_list_goals_household_isolation(self):
        """Users only see goals from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        Goal.objects.create(
            household=household1,
            name="Goal 1",
            target_amount=1000,
            due_date=timezone.now().date(),
        )
        Goal.objects.create(
            household=household2,
            name="Goal 2",
            target_amount=2000,
            due_date=timezone.now().date(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/goals/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Goal 1"


@pytest.mark.django_db
class TestGoalViewSetCreate:
    """Test goal creation endpoint."""

    def test_create_goal_valid(self):
        """Can create a valid goal."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "name": "Emergency Fund",
            "target_amount": "10000.00",
            "due_date": (timezone.now() + timedelta(days=365)).date().isoformat(),
        }

        response = client.post("/api/v1/goals/", data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Emergency Fund"


@pytest.mark.django_db
class TestGoalProgressListAction:
    """Test progress_list custom action."""

    def test_get_goal_progress_list(self):
        """Can retrieve progress list for a goal."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        goal = Goal.objects.create(
            household=household,
            name="Savings",
            target_amount=Decimal("5000.00"),
            due_date=(timezone.now() + timedelta(days=365)).date(),
        )
        GoalProgress.objects.create(
            goal=goal, amount_added=Decimal("100.00"), date_added=timezone.now().date()
        )
        GoalProgress.objects.create(
            goal=goal, amount_added=Decimal("200.00"), date_added=timezone.now().date()
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/goals/{goal.id}/progress/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestGoalAddProgressAction:
    """Test add_progress custom action."""

    def test_add_progress_to_goal(self):
        """Can add progress contribution to goal."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        goal = Goal.objects.create(
            household=household,
            name="Vacation Fund",
            target_amount=Decimal("5000.00"),
            current_amount=Decimal("1000.00"),
            due_date=(timezone.now() + timedelta(days=365)).date(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "amount_added": "500.00",
            "date_added": timezone.now().date().isoformat(),
        }

        response = client.post(
            f"/api/v1/goals/{goal.id}/add-progress/", data, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

        goal.refresh_from_db()
        assert goal.current_amount == Decimal("1500.00")

    def test_add_progress_with_milestone(self):
        """Adding progress updates milestone stickers."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        goal = Goal.objects.create(
            household=household,
            name="Goal with Milestones",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("0.00"),
            milestone_amount=Decimal("100.00"),
            due_date=(timezone.now() + timedelta(days=365)).date(),
        )

        client = APIClient()
        client.force_authenticate(user=user)

        data = {
            "amount_added": "250.00",
            "date_added": timezone.now().date().isoformat(),
        }

        response = client.post(
            f"/api/v1/goals/{goal.id}/add-progress/", data, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

        goal.refresh_from_db()
        assert goal.current_amount == Decimal("250.00")
        assert goal.sticker_count > 0  # Should have earned stickers


@pytest.mark.django_db
class TestGoalProgressViewSet:
    """Test GoalProgress viewset."""

    def test_list_goal_progress(self):
        """Can list goal progress entries."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )
        goal = Goal.objects.create(
            household=household,
            name="Savings",
            target_amount=Decimal("5000.00"),
            due_date=(timezone.now() + timedelta(days=365)).date(),
        )
        GoalProgress.objects.create(
            goal=goal, amount_added=Decimal("100.00"), date_added=timezone.now().date()
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/goal-progress/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_goal_progress_household_isolation(self):
        """Users only see progress from their household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass123",
            first_name="User1",
            household=household1,
        )

        goal1 = Goal.objects.create(
            household=household1,
            name="Goal 1",
            target_amount=1000,
            due_date=timezone.now().date(),
        )
        goal2 = Goal.objects.create(
            household=household2,
            name="Goal 2",
            target_amount=2000,
            due_date=timezone.now().date(),
        )

        GoalProgress.objects.create(
            goal=goal1, amount_added=100, date_added=timezone.now().date()
        )
        GoalProgress.objects.create(
            goal=goal2, amount_added=200, date_added=timezone.now().date()
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/goal-progress/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
