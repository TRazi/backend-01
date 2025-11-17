# apps/categories/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Sum, Count

from apps.common.models import BaseModel
from apps.categories.enums import CATEGORY_TYPE_CHOICES


class Category(BaseModel):
    """
    Represents a transaction category for organizing and reporting.

    Key features:
    - Household-specific categories (each household can customize)
    - Hierarchical support (parent/child categories)
    - Type-based (income, expense, or both)
    - Soft deletion to preserve transaction history
    - Usage statistics via computed properties

    Examples:
    - Groceries (parent: Food & Dining)
    - Salary (type: income)
    - Rent (type: expense)
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="categories",
        help_text="Household this category belongs to",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100, help_text="Category name (e.g., 'Groceries', 'Salary')"
    )

    description = models.TextField(
        blank=True, help_text="Optional description of what belongs in this category"
    )

    # Category type
    category_type = models.CharField(
        max_length=10,
        choices=CATEGORY_TYPE_CHOICES,
        default="expense",
        help_text="Whether this category is for income, expense, or both",
    )

    # Hierarchical categories (parent/child)
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
        help_text="Parent category (for hierarchical organization)",
    )

    # Display settings
    icon = models.CharField(
        max_length=50, blank=True, help_text="Icon name or emoji for UI display"
    )

    color = models.CharField(
        max_length=7,
        default="#6B7280",
        help_text="Hex color for UI display (e.g., '#FF5733')",
    )

    # Ordering and status
    display_order = models.PositiveIntegerField(
        default=0, help_text="Order for displaying categories in UI"
    )

    is_active = models.BooleanField(
        default=True, help_text="Whether this category is active"
    )

    is_deleted = models.BooleanField(
        default=False, help_text="Soft delete flag - preserves transaction history"
    )

    # System category flag (for default categories)
    is_system = models.BooleanField(
        default=False, help_text="Whether this is a system-provided default category"
    )

    # Budget tracking
    is_budgetable = models.BooleanField(
        default=True, help_text="Whether this category can have budgets assigned"
    )

    class Meta:
        db_table = "categories"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        unique_together = [["household", "name", "is_deleted"]]
        indexes = [
            models.Index(fields=["household", "is_active", "is_deleted"]),
            models.Index(fields=["household", "category_type", "is_deleted"]),
            models.Index(fields=["parent"]),
            models.Index(fields=["is_system"]),
        ]
        ordering = ["display_order", "name"]

    def __str__(self):
        deleted = " (Deleted)" if self.is_deleted else ""
        if self.parent:
            return f"{self.parent.name} > {self.name}{deleted}"
        return f"{self.name}{deleted}"

    def clean(self):
        """Validate category data."""
        super().clean()

        # Prevent self-referencing parent
        if self.parent == self:
            raise ValidationError("Category cannot be its own parent")

        # Prevent circular references (A -> B -> A)
        if self.parent:
            current = self.parent
            depth = 0
            while current and depth < 10:  # Prevent infinite loop
                if current == self:
                    raise ValidationError("Circular parent relationship detected")
                current = current.parent
                depth += 1

        # Ensure parent belongs to same household
        if self.parent and self.parent.household != self.household:
            raise ValidationError("Parent category must belong to same household")

        # Validate category name uniqueness within household (excluding deleted)
        existing = Category.objects.filter(
            household=self.household, name__iexact=self.name, is_deleted=False
        ).exclude(pk=self.pk)

        if existing.exists():
            raise ValidationError(
                f"Category '{self.name}' already exists in this household"
            )

    @property
    def full_path(self):
        """Get full category path (e.g., 'Food & Dining > Groceries')."""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name

    @property
    def has_subcategories(self):
        """Check if category has child categories."""
        return self.subcategories.filter(is_deleted=False).exists()

    def get_all_subcategories(self):
        """Get all subcategories recursively (excluding deleted)."""
        subcats = list(self.subcategories.filter(is_deleted=False))
        for subcat in self.subcategories.filter(is_deleted=False):
            subcats.extend(subcat.get_all_subcategories())
        return subcats

    def get_transaction_count(self):
        """Get count of transactions in this category."""
        return self.transactions.filter(status="completed").count()

    def get_total_amount(self):
        """Get total amount of completed transactions in this category."""
        total = self.transactions.filter(status="completed").aggregate(
            total=Sum("amount")
        )["total"]
        return total or 0

    def get_usage_stats(self):
        """Get comprehensive usage statistics."""
        stats = self.transactions.filter(status="completed").aggregate(
            count=Count("id"), total=Sum("amount")
        )
        return {
            "transaction_count": stats["count"] or 0,
            "total_amount": stats["total"] or 0,
            "has_transactions": (stats["count"] or 0) > 0,
        }
