# apps/budgets/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum

from apps.common.models import BaseModel
from apps.budgets.enums import BUDGET_STATUS_CHOICES, BUDGET_PERIOD_CHOICES


class Budget(BaseModel):
    """
    Represents a budget period for a household.

    Key features:
    - Time-bound budget periods (start_date to end_date)
    - Total budget amount with category breakdown
    - Automatic status tracking (active, completed, exceeded)
    - Spending tracking against budget

    Budget structure:
    - Budget: Overall container (e.g., "January 2024 Budget")
    - BudgetItems: Category-specific allocations
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="budgets",
        help_text="Household this budget belongs to",
    )

    name = models.CharField(
        max_length=255, help_text="Budget name (e.g., 'January 2024 Budget', 'Q1 2024')"
    )

    # Budget period
    start_date = models.DateField(help_text="Budget period start date")

    end_date = models.DateField(help_text="Budget period end date")

    cycle_type = models.CharField(
        max_length=20,
        choices=BUDGET_PERIOD_CHOICES,
        default="monthly",
        help_text="Budget cycle/period type",
    )

    # Budget amounts
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Total budget amount for this period"
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=BUDGET_STATUS_CHOICES,
        default="active",
        help_text="Current budget status",
    )

    # Settings
    alert_threshold = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=80.00,
        help_text="Alert when spending reaches this percentage (e.g., 80.00)",
    )

    rollover_enabled = models.BooleanField(
        default=False, help_text="Whether unused budget rolls over to next period"
    )

    notes = models.TextField(blank=True, help_text="Optional budget notes")

    class Meta:
        db_table = "budgets"
        verbose_name = "Budget"
        verbose_name_plural = "Budgets"
        indexes = [
            models.Index(fields=["household", "start_date", "end_date"]),
            models.Index(fields=["household", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        ordering = ["-start_date", "-created_at"]

    def __str__(self):
        return f"{self.name} ({self.household.name})"

    def clean(self):
        """Validate budget data."""
        super().clean()

        # Validate date range
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                raise ValidationError("start_date must be before end_date")

        # Validate total_amount is positive
        if self.total_amount <= 0:
            raise ValidationError("total_amount must be greater than zero")

        # Validate alert_threshold range
        if not (0 <= self.alert_threshold <= 100):
            raise ValidationError("alert_threshold must be between 0 and 100")

    @property
    def is_active(self):
        """Check if budget is currently active."""
        now = timezone.now().date()
        return self.status == "active" and self.start_date <= now <= self.end_date

    @property
    def is_expired(self):
        """Check if budget period has ended."""
        return timezone.now().date() > self.end_date

    @property
    def days_remaining(self):
        """Calculate days remaining in budget period."""
        if self.is_expired:
            return 0
        delta = self.end_date - timezone.now().date()
        return max(0, delta.days)

    def get_total_spent(self):
        """Calculate total spent in this budget period."""
        from transactions.models import Transaction

        total = Transaction.objects.filter(
            account__household=self.household,
            date__gte=self.start_date,
            date__lte=self.end_date,
            status="completed",
            transaction_type="expense",
        ).aggregate(total=Sum("amount"))["total"]

        return abs(total) if total else 0

    def get_total_remaining(self):
        """Calculate remaining budget amount."""
        return self.total_amount - self.get_total_spent()

    def get_utilization_percentage(self):
        """Calculate budget utilization as percentage."""
        spent = self.get_total_spent()
        if self.total_amount == 0:
            return 0
        return (spent / self.total_amount) * 100

    def is_over_budget(self):
        """Check if spending has exceeded budget."""
        return self.get_total_spent() > self.total_amount

    def should_alert(self):
        """Check if alert threshold has been reached."""
        return self.get_utilization_percentage() >= self.alert_threshold


class BudgetItem(BaseModel):
    """
    Represents a category-specific budget allocation within a Budget.

    Example:
    - Budget: "January 2024" (total: $2000)
      - BudgetItem: "Groceries" ($500)
      - BudgetItem: "Transportation" ($300)
      - BudgetItem: "Entertainment" ($200)
    """

    budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Parent budget this item belongs to",
    )

    name = models.CharField(max_length=255, help_text="Budget item name")

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Allocated amount for this budget item",
    )

    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="budget_items",
        help_text="Category this budget item tracks (optional)",
    )

    notes = models.TextField(
        blank=True, help_text="Optional notes for this budget item"
    )

    class Meta:
        db_table = "budget_items"
        verbose_name = "Budget Item"
        verbose_name_plural = "Budget Items"
        unique_together = [["budget", "name"]]
        indexes = [
            models.Index(fields=["budget", "category"]),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} - ${self.amount} ({self.budget.name})"

    def clean(self):
        """Validate budget item data."""
        super().clean()

        # Validate amount is positive
        if self.amount <= 0:
            raise ValidationError("amount must be greater than zero")

        # Ensure category belongs to same household as budget
        if self.category and self.category.household != self.budget.household:
            raise ValidationError(
                "Category must belong to the same household as budget"
            )

    def get_spent(self):
        """Calculate amount spent in this budget item's category."""
        from transactions.models import Transaction

        if not self.category:
            return 0

        total = Transaction.objects.filter(
            category=self.category,
            date__gte=self.budget.start_date,
            date__lte=self.budget.end_date,
            status="completed",
            transaction_type="expense",
        ).aggregate(total=Sum("amount"))["total"]

        return abs(total) if total else 0

    def get_remaining(self):
        """Calculate remaining budget for this item."""
        return self.amount - self.get_spent()

    def get_utilization_percentage(self):
        """Calculate utilization percentage for this item."""
        spent = self.get_spent()
        if self.amount == 0:
            return 0
        return (spent / self.amount) * 100

    def is_over_budget(self):
        """Check if this item is over budget."""
        return self.get_spent() > self.amount
