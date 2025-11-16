# apps/goals/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal

from common.models import BaseModel
from goals.enums import GOAL_STATUS_CHOICES, GOAL_TYPE_CHOICES


class Goal(BaseModel):
    """
    Represents a savings or financial goal for a household.

    Key features:
    - Target amount tracking with current progress
    - Due date for accountability
    - Gamification via milestones and stickers
    - Progress tracking with GoalProgress records
    - Automatic completion detection

    Examples:
    - "Holiday Fund" - $5,000 by Dec 2024
    - "Emergency Fund" - $10,000 by Jun 2025
    - "New Car" - $15,000 by Dec 2025
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="goals",
        help_text="Household this goal belongs to",
    )

    name = models.CharField(
        max_length=255, help_text="Goal name (e.g., 'Holiday Fund', 'Emergency Fund')"
    )

    description = models.TextField(
        blank=True, help_text="Optional detailed description of the goal"
    )

    goal_type = models.CharField(
        max_length=20,
        choices=GOAL_TYPE_CHOICES,
        default="savings",
        help_text="Type of goal",
    )

    # Financial targets
    target_amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Target amount to reach"
    )

    current_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Current progress towards goal (updated via service)",
    )

    # Timeline
    due_date = models.DateField(help_text="Target completion date")

    # Status
    status = models.CharField(
        max_length=20,
        choices=GOAL_STATUS_CHOICES,
        default="active",
        help_text="Current goal status",
    )

    # Gamification - Milestones and stickers
    milestone_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount per milestone (e.g., $500 earns a sticker)",
    )

    sticker_count = models.PositiveIntegerField(
        default=0, help_text="Number of stickers/milestones earned"
    )

    # Settings
    auto_contribute = models.BooleanField(
        default=False, help_text="Whether to auto-contribute from transactions"
    )

    contribution_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage of income to auto-contribute (if enabled)",
    )

    # Visual settings
    icon = models.CharField(
        max_length=50, blank=True, help_text="Icon or emoji for goal display"
    )

    color = models.CharField(
        max_length=7, default="#10B981", help_text="Hex color for UI display"
    )

    image = models.ImageField(
        upload_to="goals/%Y/%m/",
        null=True,
        blank=True,
        help_text="Optional image for goal visualization",
    )

    class Meta:
        db_table = "goals"
        verbose_name = "Goal"
        verbose_name_plural = "Goals"
        indexes = [
            models.Index(fields=["household", "status"]),
            models.Index(fields=["household", "due_date"]),
            models.Index(fields=["status", "due_date"]),
        ]
        ordering = ["due_date", "name"]

    def __str__(self):
        return f"{self.name} ({self.household.name})"

    def clean(self):
        """Validate goal data."""
        super().clean()

        # Validate target_amount is positive
        if self.target_amount <= 0:
            raise ValidationError("target_amount must be greater than zero")

        # Validate current_amount doesn't exceed target
        if self.current_amount > self.target_amount:
            raise ValidationError("current_amount cannot exceed target_amount")

        # Validate due_date is in future (for new goals)
        if not self.pk and self.due_date <= timezone.now().date():
            raise ValidationError("due_date must be in the future")

        # Validate contribution_percentage range
        if self.contribution_percentage is not None:
            if not (0 <= self.contribution_percentage <= 100):
                raise ValidationError(
                    "contribution_percentage must be between 0 and 100"
                )

        # Validate milestone_amount
        if self.milestone_amount:
            if self.milestone_amount <= 0:
                raise ValidationError("milestone_amount must be greater than zero")
            if self.milestone_amount > self.target_amount:
                raise ValidationError("milestone_amount cannot exceed target_amount")

    @property
    def progress_percentage(self):
        """Calculate progress as percentage."""
        if self.target_amount == 0:
            return 0
        return float((Decimal(str(self.current_amount)) / self.target_amount) * 100)

    @property
    def remaining_amount(self):
        """Calculate remaining amount to reach goal."""
        return self.target_amount - Decimal(str(self.current_amount))

    @property
    def is_completed(self):
        """Check if goal has been completed."""
        return self.current_amount >= self.target_amount

    @property
    def is_overdue(self):
        """Check if goal is past due date."""
        return timezone.now().date() > self.due_date and not self.is_completed

    @property
    def days_remaining(self):
        """Calculate days until due date."""
        if self.is_completed:
            return 0
        delta = self.due_date - timezone.now().date()
        return max(0, delta.days)

    @property
    def expected_milestones(self):
        """Calculate expected number of milestones based on target."""
        if not self.milestone_amount or self.milestone_amount == 0:
            return 0
        return int(self.target_amount / self.milestone_amount)

    def calculate_stickers_earned(self):
        """
        Calculate number of stickers earned based on current progress.
        Updates sticker_count field.
        """
        if not self.milestone_amount or self.milestone_amount == 0:
            return 0

        earned = int(self.current_amount / self.milestone_amount)
        return earned

    def get_contribution_history(self):
        """Get all contributions to this goal."""
        return self.progress_records.all().order_by("-date_added")

    def get_total_contributed(self):
        """Calculate total amount contributed (from GoalProgress records)."""
        total = self.progress_records.aggregate(total=Sum("amount_added"))["total"]
        return total or 0


class GoalProgress(BaseModel):
    """
    Tracks individual contributions/progress updates to a goal.

    Used for:
    - Historical tracking of contributions
    - Gamification milestone detection
    - Progress visualization over time
    """

    goal = models.ForeignKey(
        "goals.Goal",
        on_delete=models.CASCADE,
        related_name="progress_records",
        help_text="Goal this progress record belongs to",
    )

    amount_added = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount added to goal in this contribution",
    )

    date_added = models.DateTimeField(
        default=timezone.now, help_text="When this contribution was made"
    )

    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="goal_progress",
        help_text="Optional linked transaction for this contribution",
    )

    notes = models.TextField(
        blank=True, help_text="Optional notes about this contribution"
    )

    milestone_reached = models.BooleanField(
        default=False,
        help_text="Whether this contribution triggered a milestone/sticker",
    )

    class Meta:
        db_table = "goal_progress"
        verbose_name = "Goal Progress"
        verbose_name_plural = "Goal Progress Records"
        indexes = [
            models.Index(fields=["goal", "date_added"]),
            models.Index(fields=["date_added"]),
        ]
        ordering = ["-date_added"]

    def __str__(self):
        return f"{self.goal.name} - ${self.amount_added} on {self.date_added.strftime('%Y-%m-%d')}"

    def clean(self):
        """Validate goal progress data."""
        super().clean()

        # Validate amount_added is positive
        if self.amount_added <= 0:
            raise ValidationError("amount_added must be greater than zero")

        # Validate transaction belongs to same household
        if self.transaction:
            if self.transaction.account.household != self.goal.household:
                raise ValidationError(
                    "Transaction must belong to the same household as goal"
                )
