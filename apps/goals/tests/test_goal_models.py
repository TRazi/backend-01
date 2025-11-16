"""
Tests for goals app models.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone

from goals.models import Goal, GoalProgress
from households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalModel:
    """Test Goal model methods and properties."""

    def test_str_method(self):
        """Test __str__ method returns goal name with household."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save for vacation",
            target_amount=5000.00,
            due_date=date(2025, 12, 31),
        )
        assert str(goal) == "Save for vacation (Test Household)"

    def test_progress_percentage_property(self):
        """Test progress_percentage calculates correctly."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save $1000",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("250.00"),
            due_date=date(2026, 12, 31),
        )
        assert goal.progress_percentage == Decimal("25.0")

    def test_progress_percentage_zero_target(self):
        """Test progress_percentage returns 0 when target is zero."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Zero Target Goal",
            target_amount=Decimal("0.00"),
            current_amount=Decimal("100.00"),
            due_date=date(2026, 12, 31),
        )
        assert goal.progress_percentage == Decimal("0")

    def test_remaining_amount_property(self):
        """Test remaining_amount calculates correctly."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save $1000",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("400.00"),
            due_date=date(2026, 12, 31),
        )
        assert goal.remaining_amount == Decimal("600.00")

    def test_is_completed_property_true(self):
        """Test is_completed returns True when goal is met."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Completed Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("1000.00"),
            due_date=date(2026, 12, 31),
        )
        assert goal.is_completed is True

    def test_is_completed_property_false(self):
        """Test is_completed returns False when goal is not met."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="In Progress Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=date(2026, 12, 31),
        )
        assert goal.is_completed is False

    def test_is_overdue_property_true(self):
        """Test is_overdue returns True for past due goals."""
        household = Household.objects.create(name="Test Household")
        past_date = date.today() - timedelta(days=5)
        goal = Goal.objects.create(
            household=household,
            name="Overdue Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=past_date,
        )
        assert goal.is_overdue is True

    def test_is_overdue_property_false(self):
        """Test is_overdue returns False for future goals."""
        household = Household.objects.create(name="Test Household")
        future_date = date.today() + timedelta(days=30)
        goal = Goal.objects.create(
            household=household,
            name="Future Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("500.00"),
            due_date=future_date,
        )
        assert goal.is_overdue is False

    def test_days_remaining_property_positive(self):
        """Test days_remaining returns positive number for future goals."""
        household = Household.objects.create(name="Test Household")
        future_date = date.today() + timedelta(days=10)
        goal = Goal.objects.create(
            household=household,
            name="Future Goal",
            target_amount=Decimal("1000.00"),
            due_date=future_date,
        )
        assert goal.days_remaining in [10, 11]

    def test_days_remaining_property_negative(self):
        """Test days_remaining returns 0 for overdue goals (max(0, delta.days))."""
        household = Household.objects.create(name="Test Household")
        past_date = date.today() - timedelta(days=5)
        goal = Goal.objects.create(
            household=household,
            name="Overdue Goal",
            target_amount=Decimal("1000.00"),
            due_date=past_date,
        )
        # Model uses max(0, delta.days) so overdue goals return 0
        assert goal.days_remaining == 0

    def test_expected_milestones_property(self):
        """Test expected_milestones calculates correctly."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Milestone Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("250.00"),
            milestone_amount=Decimal("100.00"),
            due_date=date(2026, 12, 31),
        )
        assert goal.expected_milestones == 10

    def test_calculate_stickers_earned(self):
        """Test calculate_stickers_earned method."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Sticker Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("350.00"),
            milestone_amount=Decimal("100.00"),
            due_date=date(2026, 12, 31),
        )
        stickers = goal.calculate_stickers_earned()
        assert stickers == 3

    def test_get_total_contributed(self):
        """Test get_total_contributed method."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Contribution Goal",
            target_amount=Decimal("1000.00"),
            due_date=date(2026, 12, 31),
        )
        # Add some progress entries
        GoalProgress.objects.create(goal=goal, amount_added=Decimal("100.00"))
        GoalProgress.objects.create(goal=goal, amount_added=Decimal("150.00"))
        GoalProgress.objects.create(goal=goal, amount_added=Decimal("50.00"))

        total = goal.get_total_contributed()
        assert total == Decimal("300.00")


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalProgressModel:
    """Test GoalProgress model methods."""

    def test_str_method(self):
        """Test __str__ returns formatted string with date."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Test Goal",
            target_amount=Decimal("1000.00"),
            due_date=date(2026, 12, 31),
        )
        test_date = timezone.now()
        progress = GoalProgress.objects.create(
            goal=goal, amount_added=Decimal("100.00"), date_added=test_date
        )
        expected = f"Test Goal - $100.00 on {test_date.strftime('%Y-%m-%d')}"
        assert str(progress) == expected
