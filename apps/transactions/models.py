# apps/transactions/models.py
import uuid
from django.db import models
from django.core.exceptions import ValidationError

from common.models import BaseModel
from transactions.enums import (
    TRANSACTION_TYPE_CHOICES,
    TRANSACTION_STATUS_CHOICES,
    TRANSACTION_SOURCE_CHOICES,
)


class Transaction(BaseModel):
    """
    Represents a financial transaction (income, expense, or transfer).

    Key identifiers:
    - id: Internal database key
    - uuid: External API identifier (prevents enumeration, enables webhooks/idempotency)

    Key features:
    - Explicit transaction_type (not derived from amount)
    - Status tracking (pending, completed, failed, cancelled)
    - Multiple entry methods (manual, voice, receipt OCR)
    - Flexible categorization via Category + Tags
    - Balance updates handled by transaction service layer

    Business rules:
    - Expenses should have negative amounts
    - Income should have positive amounts
    - Transfers handled via paired transactions
    """

    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Unique identifier for API, webhooks, and idempotent imports",
    )

    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.CASCADE,
        related_name="transactions",
        help_text="Account this transaction belongs to",
    )

    # Optional links to budget/goal
    goal = models.ForeignKey(
        "goals.Goal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Goal this transaction contributes to (if applicable)",
    )

    budget = models.ForeignKey(
        "budgets.Budget",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Budget this transaction is tracked against",
    )

    # Transaction details
    transaction_type = models.CharField(
        max_length=20, choices=TRANSACTION_TYPE_CHOICES, help_text="Type of transaction"
    )

    status = models.CharField(
        max_length=20,
        choices=TRANSACTION_STATUS_CHOICES,
        default="completed",
        help_text="Current transaction status",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Transaction amount (positive for income, negative for expense)",
    )

    description = models.CharField(max_length=500, help_text="Transaction description")

    date = models.DateTimeField(help_text="When the transaction occurred")

    # Categorization
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Primary transaction category",
    )

    tags = models.ManyToManyField(
        "transactions.TransactionTag",
        blank=True,
        related_name="transactions",
        help_text="Additional tags for flexible categorization",
    )

    # Entry method tracking
    receipt_image = models.ImageField(
        upload_to="receipts/%Y/%m/",
        null=True,
        blank=True,
        help_text="Uploaded receipt image (if entered via OCR)",
    )

    voice_entry_flag = models.BooleanField(
        default=False, help_text="Whether this was entered via voice"
    )

    transaction_source = models.CharField(
        max_length=20,
        choices=TRANSACTION_SOURCE_CHOICES,
        default="manual",
        help_text="How this transaction was entered",
    )

    # Additional metadata
    merchant = models.CharField(
        max_length=255, blank=True, help_text="Merchant/vendor name"
    )

    notes = models.TextField(blank=True, help_text="Additional notes")

    is_recurring = models.BooleanField(
        default=False, help_text="Whether this is a recurring transaction"
    )

    # Transfer linkage (if transfer type)
    linked_transaction = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_pair",
        help_text="Linked transaction for transfers (opposite account)",
    )

    class Meta:
        db_table = "transactions"
        verbose_name = "Transaction"
        verbose_name_plural = "Transactions"
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["account", "date"]),
            models.Index(fields=["category", "date"]),
            models.Index(fields=["transaction_type", "status", "date"]),
            models.Index(fields=["date"]),
            models.Index(fields=["account", "-date"]),
            models.Index(fields=["status", "date"]),
        ]
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.description} - ${self.amount} ({self.date.strftime('%Y-%m-%d')})"

    def clean(self):
        """Validate transaction data."""
        super().clean()

        # Validate amount is not zero
        if self.amount == 0:
            raise ValidationError("Transaction amount cannot be zero")

        # Validate amount sign matches transaction type
        if self.transaction_type == "expense" and self.amount > 0:
            raise ValidationError("Expense transactions must have negative amounts")

        if self.transaction_type == "income" and self.amount < 0:
            raise ValidationError("Income transactions must have positive amounts")

        # Ensure account belongs to same household as budget/goal
        if self.budget and self.budget.household != self.account.household:
            raise ValidationError("Budget must belong to the same household as account")

        if self.goal and self.goal.household != self.account.household:
            raise ValidationError("Goal must belong to the same household as account")

        # Transfer validations
        if self.transaction_type == "transfer" and not self.linked_transaction:
            raise ValidationError(
                "Transfer transactions must have a linked_transaction"
            )

    @property
    def is_pending(self):
        """Check if transaction is pending."""
        return self.status == "pending"

    @property
    def is_completed(self):
        """Check if transaction is completed."""
        return self.status == "completed"


class TransactionTag(BaseModel):
    """
    Tags for flexible, multi-dimensional transaction categorization.

    Examples: 'tax-deductible', 'reimbursable', 'vacation', 'health'
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="transaction_tags",
        help_text="Household this tag belongs to",
    )

    name = models.CharField(max_length=50, help_text="Tag name")

    color = models.CharField(
        max_length=7,
        default="#6B7280",
        help_text="Hex color for UI display (e.g., '#FF5733')",
    )

    description = models.TextField(
        blank=True, help_text="Optional description of tag usage"
    )

    class Meta:
        db_table = "transaction_tags"
        verbose_name = "Transaction Tag"
        verbose_name_plural = "Transaction Tags"
        unique_together = [["household", "name"]]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.household.name})"
