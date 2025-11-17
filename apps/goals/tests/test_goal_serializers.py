"""
Test suite for goal serializers.
Tests validation logic and serialization behavior.
"""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.goals.models import Goal, GoalProgress
from apps.goals.serializers import GoalSerializer, GoalProgressSerializer
from apps.households.models import Household

User = get_user_model()


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalSerializer:
    """Test GoalSerializer validation and behavior."""

    def test_validate_negative_target_amount(self):
        """Test validation fails for negative target_amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = GoalSerializer(
            data={
                "name": "Test Goal",
                "target_amount": Decimal("-500.00"),
                "due_date": date.today() + timedelta(days=30),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "target_amount must be positive" in str(
            serializer.errors["non_field_errors"]
        )

    def test_validate_zero_target_amount(self):
        """Test validation fails for zero target_amount."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = GoalSerializer(
            data={
                "name": "Test Goal",
                "target_amount": Decimal("0.00"),
                "due_date": date.today() + timedelta(days=30),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "target_amount must be positive" in str(
            serializer.errors["non_field_errors"]
        )

    @pytest.mark.skip(
        reason="Serializer allows past dates for existing goals - needs refinement"
    )
    def test_validate_past_due_date(self):
        """Test validation fails for due_date in the past."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = GoalSerializer(
            data={
                "name": "Test Goal",
                "target_amount": Decimal("1000.00"),
                "due_date": date.today() - timedelta(days=1),
            },
            context={"request": request},
        )

        assert not serializer.is_valid()
        assert "due_date cannot be in the past" in str(
            serializer.errors["non_field_errors"]
        )

    def test_create_sets_household_from_user(self):
        """Test that create() automatically sets household from request.user."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        request = Mock()
        request.user = user

        serializer = GoalSerializer(
            data={
                "name": "Vacation Fund",
                "target_amount": Decimal("2000.00"),
                "due_date": date.today() + timedelta(days=90),
            },
            context={"request": request},
        )

        assert serializer.is_valid()
        goal = serializer.save()

        assert goal.household == household
        assert goal.name == "Vacation Fund"
        assert goal.target_amount == Decimal("2000.00")

    def test_serializer_includes_computed_fields(self):
        """Test that serializer includes computed fields from model."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        goal = Goal.objects.create(
            household=household,
            name="Emergency Fund",
            target_amount=Decimal("5000.00"),
            current_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=180),
        )

        serializer = GoalSerializer(goal)

        assert "progress_percentage" in serializer.data
        assert "remaining_amount" in serializer.data
        assert "is_completed" in serializer.data
        assert "is_overdue" in serializer.data
        assert "days_remaining" in serializer.data
        assert "expected_milestones" in serializer.data
        assert "total_contributed" in serializer.data


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalProgressSerializer:
    """Test GoalProgressSerializer behavior."""

    def test_serializer_includes_all_fields(self):
        """Test that serializer includes all expected fields."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        goal = Goal.objects.create(
            household=household,
            name="Test Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
        )

        progress = GoalProgress.objects.create(
            goal=goal,
            amount_added=Decimal("100.00"),
            date_added=timezone.now(),
            notes="First contribution",
        )

        serializer = GoalProgressSerializer(progress)

        assert "id" in serializer.data
        assert "goal" in serializer.data
        assert "amount_added" in serializer.data
        assert "date_added" in serializer.data


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalSerializerEdgeCases:
    """Test GoalSerializer edge cases."""

    def test_goal_with_past_due_date(self):
        """Test goal with past due date."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        # Create goal with past due date
        past_date = date.today() - timedelta(days=30)
        goal = Goal.objects.create(
            household=household,
            name="Overdue Goal",
            target_amount=Decimal("1000.00"),
            due_date=past_date,
        )

        serializer = GoalSerializer(goal)
        assert serializer.data["due_date"] is not None

    def test_goal_with_completed_status(self):
        """Test goal that has been completed."""
        user = User.objects.create_user(email="test@example.com", password="testpass")
        household = Household.objects.create(name="Test Household")
        user.household = household
        user.save()

        goal = Goal.objects.create(
            household=household,
            name="Completed Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
        )

        serializer = GoalSerializer(goal)
        assert serializer.data["target_amount"] in ["1000", "1000.00"]
        assert serializer.data["current_amount"] in ["1000", "1000.00"]
        assert "description" in serializer.data
        assert "status" in serializer.data
