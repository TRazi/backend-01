"""
Tests for Goal model validation methods.
Following Django testing best practices from topics/testing/.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.goals.models import Goal
from apps.households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
class TestGoalValidation:
    """Test Goal model validation in clean() method."""

    def test_clean_validates_positive_target_amount(self):
        """Test clean raises error for non-positive target_amount."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Invalid Goal",
            target_amount=Decimal("-100.00"),
            due_date=date.today() + timedelta(days=30),
        )
        with pytest.raises(
            ValidationError, match="target_amount must be greater than zero"
        ):
            goal.clean()

    def test_clean_validates_zero_target_amount(self):
        """Test clean raises error for zero target_amount."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Zero Target Goal",
            target_amount=Decimal("0.00"),
            due_date=date.today() + timedelta(days=30),
        )
        with pytest.raises(
            ValidationError, match="target_amount must be greater than zero"
        ):
            goal.clean()

    def test_clean_validates_current_not_exceeds_target(self):
        """Test clean raises error when current_amount > target_amount."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Exceeded Goal",
            target_amount=Decimal("100.00"),
            current_amount=Decimal("150.00"),  # Greater than target
            due_date=date.today() + timedelta(days=30),
        )
        with pytest.raises(
            ValidationError, match="current_amount cannot exceed target_amount"
        ):
            goal.clean()

    def test_clean_validates_future_due_date_for_new_goal(self):
        """Test clean raises error when due_date is in past for new goal."""
        household = Household.objects.create(name="Test Household")
        past_date = date.today() - timedelta(days=5)

        goal = Goal(
            household=household,
            name="Past Due Goal",
            target_amount=Decimal("1000.00"),
            due_date=past_date,
        )
        # New goal (no pk) should raise error
        with pytest.raises(ValidationError, match="due_date must be in the future"):
            goal.clean()

    def test_clean_allows_past_due_date_for_existing_goal(self):
        """Test clean allows past due_date for existing goals."""
        household = Household.objects.create(name="Test Household")
        future_date = date.today() + timedelta(days=30)

        # Create goal with future date
        goal = Goal.objects.create(
            household=household,
            name="Existing Goal",
            target_amount=Decimal("1000.00"),
            due_date=future_date,
        )

        # Update with past date (should be allowed for existing goal)
        past_date = date.today() - timedelta(days=5)
        goal.due_date = past_date

        # Should not raise exception since goal already exists (has pk)
        goal.clean()

    def test_clean_validates_contribution_percentage_range_negative(self):
        """Test clean validates contribution_percentage is not negative."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Invalid Percentage Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
            contribution_percentage=Decimal("-10.00"),
        )
        with pytest.raises(
            ValidationError, match="contribution_percentage must be between 0 and 100"
        ):
            goal.clean()

    def test_clean_validates_contribution_percentage_range_over_100(self):
        """Test clean validates contribution_percentage is not over 100."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Over 100 Percentage Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
            contribution_percentage=Decimal("150.00"),
        )
        with pytest.raises(
            ValidationError, match="contribution_percentage must be between 0 and 100"
        ):
            goal.clean()

    def test_clean_validates_positive_milestone_amount(self):
        """Test clean raises error for non-positive milestone_amount."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Invalid Milestone Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
            milestone_amount=Decimal("-50.00"),
        )
        with pytest.raises(
            ValidationError, match="milestone_amount must be greater than zero"
        ):
            goal.clean()

    def test_clean_validates_milestone_not_exceeds_target(self):
        """Test clean raises error when milestone_amount > target_amount."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Large Milestone Goal",
            target_amount=Decimal("100.00"),
            due_date=date.today() + timedelta(days=30),
            milestone_amount=Decimal("200.00"),  # Exceeds target
        )
        with pytest.raises(
            ValidationError, match="milestone_amount cannot exceed target_amount"
        ):
            goal.clean()

    def test_clean_passes_for_valid_goal(self):
        """Test clean passes for valid goal data."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Valid Goal",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("250.00"),
            due_date=date.today() + timedelta(days=30),
            contribution_percentage=Decimal("10.00"),
            milestone_amount=Decimal("100.00"),
        )
        # Should not raise any exception
        goal.clean()

    def test_clean_passes_with_none_optional_fields(self):
        """Test clean passes when optional fields are None."""
        household = Household.objects.create(name="Test Household")
        goal = Goal(
            household=household,
            name="Simple Goal",
            target_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
            contribution_percentage=None,
            milestone_amount=None,
        )
        # Should not raise any exception
        goal.clean()
