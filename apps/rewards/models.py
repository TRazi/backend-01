# apps/rewards/models.py
from django.db import models
from django.core.exceptions import ValidationError

from apps.common.models import BaseModel
from apps.rewards.enums import REWARD_TYPE_CHOICES


class Reward(BaseModel):
    """
    Represents gamification rewards earned by users.

    Key features:
    - Achievement tracking (milestones, streaks, goals)
    - User-specific rewards
    - Visual badges/stickers for UI display
    - Timestamp tracking for earned achievements

    Examples:
    - "First Budget Created" - earned when user creates first budget
    - "Savings Milestone" - earned when goal milestone reached
    - "30-Day Streak" - earned for 30 consecutive days of logging
    - "Debt Free" - earned when debt payoff goal completed
    """

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="rewards",
        help_text="User who earned this reward",
    )

    reward_type = models.CharField(
        max_length=30, choices=REWARD_TYPE_CHOICES, help_text="Type of reward earned"
    )

    title = models.CharField(
        max_length=255, help_text="Reward title (e.g., 'Budget Master', 'Savings Star')"
    )

    description = models.TextField(
        blank=True, help_text="Description of what this reward is for"
    )

    # Visual representation
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon or emoji for reward display (e.g., '🏆', '⭐', '🎉')",
    )

    badge_image = models.ImageField(
        upload_to="rewards/badges/",
        null=True,
        blank=True,
        help_text="Optional badge image",
    )

    # Tracking
    earned_on = models.DateTimeField(help_text="When this reward was earned")

    # Points system (optional for future gamification)
    points = models.PositiveIntegerField(
        default=0, help_text="Points value of this reward"
    )

    # Related objects (what triggered this reward)
    related_goal = models.ForeignKey(
        "goals.Goal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rewards",
        help_text="Goal that triggered this reward (if applicable)",
    )

    related_budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rewards",
        help_text="Budget that triggered this reward (if applicable)",
    )

    # Visibility
    is_visible = models.BooleanField(
        default=True, help_text="Whether this reward is visible to user"
    )

    class Meta:
        db_table = "rewards"
        verbose_name = "Reward"
        verbose_name_plural = "Rewards"
        indexes = [
            models.Index(fields=["user", "earned_on"]),
            models.Index(fields=["user", "reward_type"]),
            models.Index(fields=["earned_on"]),
        ]
        ordering = ["-earned_on"]

    def __str__(self):
        return (
            f"{self.title} - {self.user.email} ({self.earned_on.strftime('%Y-%m-%d')})"
        )

    def clean(self):
        """Validate reward data."""
        super().clean()

        # Validate points is non-negative
        if self.points < 0:
            raise ValidationError("points cannot be negative")
