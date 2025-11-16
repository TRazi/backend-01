"""
Audit logging models for SOC 2 compliance.
Tracks all significant actions with before/after state and request context.
"""

from django.db import models
from django.contrib.auth import get_user_model

from common.models import BaseModel
from audit.enums import ACTION_CHOICES, EXPORT_TYPE_CHOICES


def get_user_model_lazy():
    from django.contrib.auth import get_user_model

    return get_user_model()


User = get_user_model_lazy()


class AuditLog(BaseModel):
    """
    Comprehensive audit trail for all significant system actions.

    Captures:
    - Who: user performing action
    - What: action type and affected object
    - When: timestamp (from BaseModel)
    - Where: IP address, user agent
    - Context: household, organisation
    - Changes: before/after field values
    """

    # Who performed the action
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="User who performed the action (null for system actions)",
    )

    # What action was performed
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        db_index=True,
        help_text="Type of action performed",
    )

    action_description = models.TextField(
        help_text="Human-readable description of the action"
    )

    # What was affected
    object_type = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Model name of affected object (e.g., 'Transaction', 'Budget')",
    )

    object_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True, help_text="Primary key of affected object"
    )

    object_repr = models.CharField(
        max_length=255, blank=True, help_text="String representation of affected object"
    )

    # Context
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Household context (if applicable)",
    )

    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        help_text="Organisation context (if applicable)",
    )

    # Request metadata
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, help_text="IP address of the request"
    )

    user_agent = models.TextField(
        blank=True, help_text="User agent string from request"
    )

    request_path = models.CharField(
        max_length=500, blank=True, help_text="URL path of the request"
    )

    request_method = models.CharField(
        max_length=10, blank=True, help_text="HTTP method (GET, POST, etc.)"
    )

    # Change tracking (for UPDATE actions)
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Dictionary of changed fields: {field: {'old': value, 'new': value}}",
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict, blank=True, help_text="Additional contextual data"
    )

    # Success/failure
    success = models.BooleanField(
        default=True, help_text="Whether the action was successful"
    )

    error_message = models.TextField(
        blank=True, help_text="Error message if action failed"
    )

    class Meta:
        db_table = "audit_logs"
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "user"]),
            models.Index(fields=["action_type", "-created_at"]),
            models.Index(fields=["household", "-created_at"]),
            models.Index(fields=["object_type", "object_id"]),
            models.Index(fields=["ip_address", "-created_at"]),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "System"
        return f"{user_str} - {self.action_type} - {self.created_at}"


class FailedLoginAttempt(BaseModel):
    """
    Track failed login attempts for security analysis.
    Separate from django-axes for detailed audit trail.
    """

    username = models.CharField(
        max_length=255, db_index=True, help_text="Attempted username/email"
    )

    ip_address = models.GenericIPAddressField(
        db_index=True, help_text="IP address of attempt"
    )

    user_agent = models.TextField(blank=True, help_text="User agent string")

    request_path = models.CharField(
        max_length=500, blank=True, help_text="Login endpoint path"
    )

    # Track pattern detection
    attempt_count = models.PositiveIntegerField(
        default=1, help_text="Number of consecutive failures from this IP"
    )

    locked_out = models.BooleanField(
        default=False, help_text="Whether this attempt resulted in account lockout"
    )

    # Resolution
    resolved = models.BooleanField(
        default=False, help_text="Whether this security event has been reviewed"
    )

    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_login_attempts",
        help_text="Admin who reviewed this attempt",
    )

    notes = models.TextField(
        blank=True, help_text="Admin notes about this security event"
    )

    class Meta:
        db_table = "failed_login_attempts"
        verbose_name = "Failed Login Attempt"
        verbose_name_plural = "Failed Login Attempts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "ip_address"]),
            models.Index(fields=["username", "-created_at"]),
            models.Index(fields=["resolved", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.username} from {self.ip_address} at {self.created_at}"


class DataExportLog(BaseModel):
    """
    Track all data exports for compliance and security.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="data_exports",
        help_text="User who requested the export",
    )

    export_type = models.CharField(
        max_length=50,
        choices=EXPORT_TYPE_CHOICES,
        db_index=True,
        help_text="Type of data export",
    )

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="data_exports",
        help_text="Household context",
    )

    # What was exported
    record_count = models.PositiveIntegerField(help_text="Number of records exported")

    date_range_start = models.DateField(
        null=True, blank=True, help_text="Start date of exported data range"
    )

    date_range_end = models.DateField(
        null=True, blank=True, help_text="End date of exported data range"
    )

    # Request context
    ip_address = models.GenericIPAddressField(help_text="IP address of export request")

    user_agent = models.TextField(blank=True, help_text="User agent string")

    # File information
    file_format = models.CharField(
        max_length=20,
        default="json",
        help_text="Export file format (json, csv, xlsx, pdf)",
    )

    file_size_bytes = models.PositiveIntegerField(
        null=True, blank=True, help_text="Size of exported file in bytes"
    )

    # Additional filters/parameters
    export_filters = models.JSONField(
        default=dict, blank=True, help_text="Filters applied to export"
    )

    class Meta:
        db_table = "data_export_logs"
        verbose_name = "Data Export Log"
        verbose_name_plural = "Data Export Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "user"]),
            models.Index(fields=["export_type", "-created_at"]),
            models.Index(fields=["household", "-created_at"]),
        ]

    def __str__(self):
        user_str = self.user.email if self.user else "Unknown"
        return f"{user_str} - {self.export_type} - {self.created_at}"
