# apps/bills/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.common.models import BaseModel
from apps.bills.enums import BILL_STATUS_CHOICES, BILL_FREQUENCY_CHOICES


class Bill(BaseModel):
    """
    Represents a bill or recurring payment for a household.

    Key features:
    - Recurring payment tracking (weekly, monthly, etc.)
    - Due date reminders and overdue detection
    - Payment history via linked transactions
    - Auto-creation of next bill instance

    Examples:
    - Monthly rent ($1,200 due on 1st)
    - Weekly groceries budget ($150 due every Monday)
    - Quarterly insurance ($400 due every 3 months)
    """

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="bills",
        help_text="Household this bill belongs to",
    )

    name = models.CharField(
        max_length=255, help_text="Bill name (e.g., 'Rent', 'Electricity', 'Internet')"
    )

    description = models.TextField(blank=True, help_text="Optional bill description")

    # Financial details
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Bill amount"
    )

    # Schedule
    due_date = models.DateField(help_text="When this bill is due")

    frequency = models.CharField(
        max_length=20,
        choices=BILL_FREQUENCY_CHOICES,
        default="monthly",
        help_text="How often this bill recurs",
    )

    is_recurring = models.BooleanField(
        default=True, help_text="Whether this bill repeats"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=BILL_STATUS_CHOICES,
        default="pending",
        help_text="Current bill status",
    )

    # Payment tracking
    paid_date = models.DateField(
        null=True, blank=True, help_text="When this bill was paid"
    )

    transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
        help_text="Transaction that paid this bill",
    )

    # Category link
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
        help_text="Category for this bill",
    )

    # Account link (which account pays this bill)
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bills",
        help_text="Account used to pay this bill",
    )

    # Reminder settings
    reminder_days_before = models.PositiveIntegerField(
        default=3, help_text="Days before due date to send reminder"
    )

    auto_pay_enabled = models.BooleanField(
        default=False, help_text="Whether this bill is set up for automatic payment"
    )

    # Visual settings
    color = models.CharField(
        max_length=7, default="#EF4444", help_text="Hex color for UI display"
    )

    notes = models.TextField(blank=True, help_text="Additional notes about this bill")

    # Next bill tracking (for recurring bills)
    next_bill = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="previous_bill",
        help_text="Next instance of this recurring bill",
    )

    class Meta:
        db_table = "bills"
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        indexes = [
            models.Index(fields=["household", "due_date"]),
            models.Index(fields=["household", "status"]),
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["due_date"]),
        ]
        ordering = ["due_date", "name"]

    def __str__(self):
        return f"{self.name} - ${self.amount} (Due: {self.due_date})"

    def clean(self):
        """Validate bill data."""
        super().clean()

        # Validate amount is positive
        if self.amount <= 0:
            raise ValidationError("amount must be greater than zero")

        # Validate paid_date not before due_date
        if self.paid_date and self.paid_date < self.due_date:
            raise ValidationError("paid_date cannot be before due_date")

        # Ensure category/account belong to same household
        if self.category and self.category.household != self.household:
            raise ValidationError("Category must belong to the same household")

        if self.account and self.account.household != self.household:
            raise ValidationError("Account must belong to the same household")

        # If status is paid, paid_date should be set
        if self.status == "paid" and not self.paid_date:
            raise ValidationError("paid_date must be set when status is 'paid'")

    @property
    def is_overdue(self):
        """Check if bill is overdue."""
        return self.status == "pending" and timezone.now().date() > self.due_date

    @property
    def is_upcoming(self):
        """Check if bill is due within next 7 days."""
        if self.status != "pending":
            return False
        days_until_due = (self.due_date - timezone.now().date()).days
        return 0 <= days_until_due <= 7

    @property
    def days_until_due(self):
        """Calculate days until due date."""
        if self.status != "pending":
            return None
        delta = self.due_date - timezone.now().date()
        return delta.days

    @property
    def should_send_reminder(self):
        """Check if reminder should be sent."""
        if self.status != "pending":
            return False
        days_until = self.days_until_due
        return days_until is not None and days_until <= self.reminder_days_before

    def calculate_next_due_date(self):
        """
        Calculate the next due date based on frequency.

        Returns:
            date: Next due date for recurring bill
        """
        if not self.is_recurring:
            return None

        frequency_map = {
            "weekly": timedelta(weeks=1),
            "fortnightly": timedelta(weeks=2),
            "monthly": timedelta(days=30),  # Approximate
            "quarterly": timedelta(days=90),  # Approximate
            "yearly": timedelta(days=365),
        }

        delta = frequency_map.get(self.frequency)
        if delta:
            return self.due_date + delta

        return None

    def mark_as_paid(self, paid_date=None, transaction=None):
        """
        Mark bill as paid and optionally link transaction.
        Note: This is a helper method. Use service layer for actual implementation.
        """
        self.status = "paid"
        self.paid_date = paid_date or timezone.now().date()
        if transaction:
            self.transaction = transaction
        self.save(update_fields=["status", "paid_date", "transaction", "updated_at"])


class BillAttachment(BaseModel):
    """
    Stores bill/invoice images and documents.
    Supports OCR processing for automatic bill data extraction.
    """

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="attachments",
        help_text="Bill this attachment belongs to",
    )

    file = models.FileField(
        upload_to="bills/user_%s/%%Y/%%m/",
        help_text="Bill or invoice document",
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
        help_text="Whether OCR has been run on this document",
    )

    ocr_text = models.TextField(
        blank=True,
        help_text="Extracted text from OCR",
    )

    ocr_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured OCR data (provider, amount, due_date, account_number)",
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
        related_name="uploaded_bills",
        help_text="User who uploaded this bill",
    )

    class Meta:
        db_table = "bill_attachments"
        verbose_name = "Bill Attachment"
        verbose_name_plural = "Bill Attachments"
        indexes = [
            models.Index(fields=["bill", "created_at"]),
            models.Index(fields=["ocr_processed", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_name} for {self.bill}"

    def clean(self):
        """Validate attachment."""
        super().clean()

        from django.conf import settings

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
