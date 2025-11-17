"""
Receipt and Bill Attachment Models for OCR Integration

Stores receipt/bill images and extracted data from AWS Textract.
Complies with Privacy Act 2020 for NZ financial data.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.utils import timezone

import uuid

User = get_user_model()


class ReceiptAttachment(models.Model):
    """
    Stores receipt images and their extracted data from AWS Textract.
    
    Privacy: All image data encrypted at rest in S3, PII masked in logs.
    Retention: Kept for 12 months per Privacy Act 2020 requirements.
    """

    # Primary identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="receipt_attachments")
    
    # Image storage
    image = models.ImageField(
        upload_to="receipts/%Y/%m/%d/",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"]),
        ],
        help_text="Receipt image (JPG, PNG, PDF only)",
    )
    
    # Metadata
    file_size = models.IntegerField(
        validators=[MinValueValidator(0)],
        help_text="File size in bytes"
    )
    file_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA256 hash of file for deduplication"
    )
    
    # Extracted Data (from Textract)
    merchant_name = models.CharField(max_length=255, null=True, blank=True)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total amount in NZD"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GST/Tax amount"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Subtotal before tax"
    )
    receipt_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=50, null=True, blank=True)
    
    # Extraction Confidence
    confidence_scores = models.JSONField(
        default=dict,
        help_text="Confidence scores from Textract (merchant, total, date, etc.)"
    )
    extracted_data = models.JSONField(
        default=dict,
        help_text="Full extracted data including line items"
    )
    
    # Processing Status
    STATUS_CHOICES = [
        ("pending", "Pending OCR Processing"),
        ("processing", "Currently Processing"),
        ("success", "Successfully Extracted"),
        ("partial", "Partially Extracted (Manual Review Needed)"),
        ("failed", "Extraction Failed"),
        ("manual_review", "Requires Manual Review"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True
    )
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    error_code = models.CharField(max_length=50, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        help_text="Data retention expiry date (12 months per Privacy Act 2020)"
    )
    
    # Linking to transaction (optional)
    transaction = models.ForeignKey(
        "Transaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_attachments"
    )
    
    # NZ-specific fields
    merchant_normalized = models.BooleanField(
        default=False,
        help_text="True if merchant name was normalized to major NZ retailer"
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]
        verbose_name = "Receipt Attachment"
        verbose_name_plural = "Receipt Attachments"

    def __str__(self):
        return f"Receipt from {self.merchant_name or 'Unknown'} - {self.created_at.date()}"

    def save(self, *args, **kwargs):
        """Calculate expiry date on save."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=365)
        super().save(*args, **kwargs)


class ReceiptLineItem(models.Model):
    """Individual line items extracted from receipt."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        ReceiptAttachment,
        on_delete=models.CASCADE,
        related_name="line_items"
    )
    
    # Item details
    description = models.CharField(max_length=255)
    quantity = models.CharField(max_length=50, null=True, blank=True)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    line_number = models.IntegerField(help_text="Order in receipt")
    confidence = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), ],
        help_text="Textract confidence score (0-100)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ["line_number"]
        verbose_name = "Receipt Line Item"
        verbose_name_plural = "Receipt Line Items"

    def __str__(self):
        return f"{self.description} - ${self.total_price}"


class BillAttachment(models.Model):
    """
    Stores bill/invoice images and extracted data.
    
    Supports: Electricity, water, internet, phone, insurance, rent.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bill_attachments")
    
    # Image storage
    image = models.ImageField(
        upload_to="bills/%Y/%m/%d/",
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "pdf"]),
        ],
    )
    
    file_size = models.IntegerField(validators=[MinValueValidator(0)])
    file_hash = models.CharField(max_length=64, db_index=True)
    
    # Extracted data
    provider_name = models.CharField(max_length=255, null=True, blank=True)
    
    BILL_TYPE_CHOICES = [
        ("electricity", "Electricity"),
        ("water", "Water"),
        ("internet", "Internet/Broadband"),
        ("phone", "Phone/Mobile"),
        ("insurance", "Insurance"),
        ("rent", "Rent"),
        ("council_rates", "Council Rates"),
        ("other", "Other Utility"),
    ]
    bill_type = models.CharField(
        max_length=20,
        choices=BILL_TYPE_CHOICES,
        null=True,
        blank=True
    )
    
    account_number = models.CharField(max_length=100, null=True, blank=True)
    billing_period_start = models.DateField(null=True, blank=True)
    billing_period_end = models.DateField(null=True, blank=True)
    
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount due in NZD"
    )
    due_date = models.DateField(null=True, blank=True)
    previous_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Confidence and extraction
    confidence_scores = models.JSONField(default=dict)
    extracted_data = models.JSONField(default=dict)
    
    # Status
    STATUS_CHOICES = [
        ("pending", "Pending OCR Processing"),
        ("processing", "Currently Processing"),
        ("success", "Successfully Extracted"),
        ("partial", "Partially Extracted"),
        ("failed", "Extraction Failed"),
        ("manual_review", "Requires Manual Review"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True
    )
    
    error_message = models.TextField(null=True, blank=True)
    error_code = models.CharField(max_length=50, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(help_text="Data retention expiry")
    
    # Linking to bill model (if exists)
    bill = models.ForeignKey(
        "bills.Bill",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attachments"
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expires_at"]),
        ]
        verbose_name = "Bill Attachment"
        verbose_name_plural = "Bill Attachments"

    def __str__(self):
        return f"{self.provider_name or 'Unknown'} - {self.bill_type or 'Unknown'}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=365)
        super().save(*args, **kwargs)
