"""Additional tests for Goal model methods to reach 85% coverage."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.goals.models import Goal, GoalProgress
from apps.households.models import Household
from apps.users.models import User


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalMethodsEdgeCases:
    """Test edge cases for Goal model methods."""

    def test_calculate_stickers_earned_zero_milestone_amount(self):
        """Test calculate_stickers_earned returns 0 when milestone_amount is None."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="No Milestone Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=date.today() + timedelta(days=30),
            milestone_amount=None,  # No milestone set
        )
        assert goal.calculate_stickers_earned() == 0

    def test_calculate_stickers_earned_milestone_amount_zero(self):
        """Test calculate_stickers_earned returns 0 when milestone_amount is exactly 0."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Zero Milestone Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=date.today() + timedelta(days=30),
            milestone_amount=Decimal("0.00"),  # Explicitly zero
        )
        assert goal.calculate_stickers_earned() == 0

    def test_get_contribution_history(self):
        """Test get_contribution_history returns ordered progress records."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Savings Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
        )

        # Create progress records
        GoalProgress.objects.create(goal=goal, amount_added=Decimal("100.00"))
        progress2 = GoalProgress.objects.create(
            goal=goal, amount_added=Decimal("200.00")
        )

        history = goal.get_contribution_history()
        assert history.count() == 2
        # Should be ordered by -date_added (most recent first)
        assert history.first() == progress2

    def test_get_total_contributed_with_contributions(self):
        """Test get_total_contributed sums all progress records."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Savings Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
        )

        GoalProgress.objects.create(goal=goal, amount_added=Decimal("100.00"))
        GoalProgress.objects.create(goal=goal, amount_added=Decimal("250.00"))
        GoalProgress.objects.create(goal=goal, amount_added=Decimal("150.00"))

        assert goal.get_total_contributed() == Decimal("500.00")

    def test_get_total_contributed_no_contributions(self):
        """Test get_total_contributed returns 0 when no progress records exist."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="New Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
        )

        # No progress records
        assert goal.get_total_contributed() == 0
