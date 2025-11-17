# apps/transactions/models.py
import uuid
from django.db import models
from django.core.exceptions import ValidationError

from apps.common.models import BaseModel
from apps.transactions.enums import (
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


class TransactionAttachment(BaseModel):
    """
    Stores receipt images and other attachments for transactions.
    Supports OCR processing and compressed storage (12 months as per spec).
    """

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="attachments",
        help_text="Transaction this attachment belongs to",
    )

    file = models.ImageField(
        upload_to="receipts/user_%s/%%Y/%%m/",
        help_text="Receipt or invoice image",
    )

    file_name = models.CharField(
        max_length=255,
        help_text="Original filename",
    )

    file_size = models.IntegerField(
        help_text="File size in bytes",
    )

    file_type = models.CharField(
        max_length=10,
        help_text="File extension (jpg, png, pdf)",
    )

    # OCR processing status
    ocr_processed = models.BooleanField(
        default=False,
        help_text="Whether OCR has been run on this image",
    )

    ocr_text = models.TextField(
        blank=True,
        help_text="Extracted text from OCR",
    )

    ocr_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured OCR data (merchant, amount, date, items)",
    )

    ocr_confidence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Average confidence score from OCR (0-100)",
    )

    ocr_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When OCR processing completed",
    )

    ocr_error = models.TextField(
        blank=True,
        help_text="Error message if OCR failed",
    )

    # Metadata
    uploaded_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_receipts",
        help_text="User who uploaded this receipt",
    )

    class Meta:
        db_table = "transaction_attachments"
        verbose_name = "Transaction Attachment"
        verbose_name_plural = "Transaction Attachments"
        indexes = [
            models.Index(fields=["transaction", "created_at"]),
            models.Index(fields=["ocr_processed", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} for {self.transaction}"

    def clean(self):
        """Validate attachment."""
        super().clean()

        # Validate file size
        if self.file and hasattr(self.file, "size"):
            max_size = settings.RECEIPT_MAX_SIZE_MB * 1024 * 1024  # Convert to bytes
            if self.file.size > max_size:
                raise ValidationError(
                    f"File size ({self.file.size} bytes) exceeds maximum allowed "
                    f"size ({max_size} bytes)"
                )

        # Validate file type
        if (
            self.file_type
            and self.file_type.lower() not in settings.RECEIPT_ALLOWED_FORMATS
        ):
            raise ValidationError(
                f"File type '{self.file_type}' not allowed. "
                f"Allowed formats: {', '.join(settings.RECEIPT_ALLOWED_FORMATS)}"
            )


class TransactionSplit(BaseModel):
    """
    Represents a split transaction across multiple categories or household members.
    Example: Grocery bill split between food ($80) and household supplies ($20).
    """

    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="splits",
        help_text="Parent transaction being split",
    )

    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_splits",
        help_text="Category for this portion of the split",
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount for this split portion",
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Description for this split portion",
    )

    # For household member splits (e.g., flatmates)
    member = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transaction_splits",
        help_text="Household member responsible for this portion",
    )

    class Meta:
        db_table = "transaction_splits"
        verbose_name = "Transaction Split"
        verbose_name_plural = "Transaction Splits"
        indexes = [
            models.Index(fields=["transaction", "category"]),
            models.Index(fields=["member", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"Split of {self.transaction} - ${self.amount}"

    def clean(self):
        """Validate split amount."""
        super().clean()

        if self.amount == 0:
            raise ValidationError("Split amount cannot be zero")

        # Ensure split doesn't exceed transaction amount
        if self.transaction_id:
            total_splits = (
                TransactionSplit.objects.filter(transaction=self.transaction)
                .exclude(pk=self.pk)
                .aggregate(total=models.Sum("amount"))["total"]
                or 0
            )

            if abs(total_splits + self.amount) > abs(self.transaction.amount):
                raise ValidationError(
                    f"Total splits (${total_splits + self.amount}) cannot exceed "
                    f"transaction amount (${self.transaction.amount})"
                )
