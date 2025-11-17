# apps/alerts/models.py
from django.db import models
from django.core.exceptions import ValidationError

from apps.common.models import BaseModel
from apps.alerts.enums import (
    ALERT_TYPE_CHOICES,
    ALERT_PRIORITY_CHOICES,
    ALERT_STATUS_CHOICES,
)


class Alert(BaseModel):
    """
    Represents automated alerts and notifications for a household.

    Key features:
    - Budget overspending warnings
    - Bill payment reminders
    - Low balance notifications
    - Goal milestone celebrations
    - Unusual spending detection

    Examples:
    - "You've spent 80% of your Groceries budget"
    - "Rent payment due in 3 days"
    - "Checking account balance below $100"
    - "Congratulations! You reached your savings milestone"
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="Household this alert belongs to",
    )

    alert_type = models.CharField(
        max_length=30, choices=ALERT_TYPE_CHOICES, help_text="Type of alert"
    )

    priority = models.CharField(
        max_length=10,
        choices=ALERT_PRIORITY_CHOICES,
        default="medium",
        help_text="Alert priority level",
    )

    status = models.CharField(
        max_length=20,
        choices=ALERT_STATUS_CHOICES,
        default="active",
        help_text="Current alert status",
    )

    # Alert content
    message = models.TextField(help_text="Alert message displayed to user")

    title = models.CharField(
        max_length=255, blank=True, help_text="Optional alert title"
    )

    # Trigger configuration
    trigger_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Threshold value that triggered this alert (e.g., budget %, balance amount)",
    )

    # Related objects
    related_budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="Budget that triggered this alert (if applicable)",
    )

    related_bill = models.ForeignKey(
        "bills.Bill",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="Bill that triggered this alert (if applicable)",
    )

    related_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="Account that triggered this alert (if applicable)",
    )

    related_goal = models.ForeignKey(
        "goals.Goal",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="alerts",
        help_text="Goal that triggered this alert (if applicable)",
    )

    # Action tracking
    action_required = models.BooleanField(
        default=False, help_text="Whether this alert requires user action"
    )

    action_url = models.URLField(
        blank=True,
        help_text="Optional URL for alert action (e.g., link to budget page)",
    )

    # Notification settings
    sent_via_email = models.BooleanField(
        default=False, help_text="Whether this alert was sent via email"
    )

    sent_via_push = models.BooleanField(
        default=False, help_text="Whether this alert was sent via push notification"
    )

    # Dismissal tracking
    dismissed_at = models.DateTimeField(
        null=True, blank=True, help_text="When user dismissed this alert"
    )

    dismissed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dismissed_alerts",
        help_text="User who dismissed this alert",
    )

    class Meta:
        db_table = "alerts"
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        indexes = [
            models.Index(fields=["household", "status", "created_at"]),
            models.Index(fields=["household", "alert_type"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["priority", "status"]),
        ]
        ordering = ["-created_at", "-priority"]

    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.household.name}"

    def clean(self):
        """Validate alert data."""
        super().clean()

        # Ensure related objects belong to same household
        if self.related_budget and self.related_budget.household != self.household:
            raise ValidationError("Related budget must belong to the same household")

        if self.related_bill and self.related_bill.household != self.household:
            raise ValidationError("Related bill must belong to the same household")

        if self.related_account and self.related_account.household != self.household:
            raise ValidationError("Related account must belong to the same household")

        if self.related_goal and self.related_goal.household != self.household:
            raise ValidationError("Related goal must belong to the same household")

    @property
    def is_active(self):
        """Check if alert is still active."""
        return self.status == "active"

    @property
    def is_high_priority(self):
        """Check if alert is high or urgent priority."""
        return self.priority in ["high", "urgent"]
