"""
Admin interface for audit logging models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from apps.audit.models import AuditLog, FailedLoginAttempt, DataExportLog

# Template constants
PRE_FORMATTED_TEMPLATE = "<pre>{}</pre>"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for audit logs."""

    list_display = [
        "created_at",
        "user_email",
        "action_type",
        "action_description_short",
        "object_link",
        "household_link",
        "ip_address",
        "success_badge",
    ]

    list_filter = [
        "action_type",
        "success",
        "created_at",
        "object_type",
    ]

    search_fields = [
        "user__email",
        "action_description",
        "object_type",
        "ip_address",
    ]

    readonly_fields = [
        "user",
        "action_type",
        "action_description",
        "object_type",
        "object_id",
        "object_repr",
        "household",
        "organisation",
        "ip_address",
        "user_agent",
        "request_path",
        "request_method",
        "changes_formatted",
        "metadata_formatted",
        "success",
        "error_message",
        "created_at",
        "updated_at",
    ]

    date_hierarchy = "created_at"

    def user_email(self, obj):
        """Display user email or 'System'."""
        return obj.user.email if obj.user else "System"

    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"

    def action_description_short(self, obj):
        """Truncate long descriptions."""
        max_length = 60
        if len(obj.action_description) > max_length:
            return f"{obj.action_description[:max_length]}..."
        return obj.action_description

    action_description_short.short_description = "Description"

    def object_link(self, obj):
        """Create admin link to affected object if possible."""
        if not obj.object_type or not obj.object_id:
            return "-"

        # Try to create admin URL
        try:
            app_label = obj.object_type.lower()
            url = reverse(
                f"admin:{app_label}_{obj.object_type.lower()}_change",
                args=[obj.object_id],
            )
            return format_html(
                '<a href="{}">{} #{}</a>', url, obj.object_type, obj.object_id
            )
        except Exception:
            # If URL reverse fails, return plain text representation
            return f"{obj.object_type} #{obj.object_id}"

    object_link.short_description = "Object"

    def household_link(self, obj):
        """Create admin link to household."""
        if not obj.household:
            return "-"

        try:
            url = reverse("admin:households_household_change", args=[obj.household.pk])
            return format_html('<a href="{}">{}</a>', url, obj.household.name)
        except Exception:
            return obj.household.name

    household_link.short_description = "Household"

    def success_badge(self, obj):
        """Display success/failure badge."""
        if obj.success:
            return format_html('<span style="color: green;">✓ Success</span>')
        return format_html('<span style="color: red;">✗ Failed</span>')

    success_badge.short_description = "Status"

    def changes_formatted(self, obj):
        """Format changes JSON for display."""
        if not obj.changes:
            return "-"
        return format_html(PRE_FORMATTED_TEMPLATE, json.dumps(obj.changes, indent=2))

    changes_formatted.short_description = "Changes"

    def metadata_formatted(self, obj):
        """Format metadata JSON for display."""
        if not obj.metadata:
            return "-"
        return format_html(PRE_FORMATTED_TEMPLATE, json.dumps(obj.metadata, indent=2))

    metadata_formatted.short_description = "Metadata"

    def has_add_permission(self, request):
        """Audit logs should not be manually created."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs should not be modified."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted (except by superuser)."""
        return request.user.is_superuser


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    """Admin interface for failed login attempts."""

    list_display = [
        "created_at",
        "username",
        "ip_address",
        "attempt_count",
        "locked_out_badge",
        "resolved_badge",
        "resolved_by",
    ]

    list_filter = [
        "locked_out",
        "resolved",
        "created_at",
    ]

    search_fields = [
        "username",
        "ip_address",
    ]

    readonly_fields = [
        "username",
        "ip_address",
        "user_agent",
        "request_path",
        "attempt_count",
        "locked_out",
        "created_at",
        "updated_at",
    ]

    fields = [
        "username",
        "ip_address",
        "user_agent",
        "request_path",
        "attempt_count",
        "locked_out",
        "resolved",
        "resolved_by",
        "notes",
        "created_at",
        "updated_at",
    ]

    date_hierarchy = "created_at"

    def locked_out_badge(self, obj):
        """Display lockout badge."""
        if obj.locked_out:
            return format_html('<span style="color: red;">🔒 Locked</span>')
        return format_html('<span style="color: gray;">-</span>')

    locked_out_badge.short_description = "Lockout"

    def resolved_badge(self, obj):
        """Display resolved status."""
        if obj.resolved:
            return format_html('<span style="color: green;">✓ Resolved</span>')
        return format_html('<span style="color: orange;">⚠ Pending</span>')

    resolved_badge.short_description = "Status"

    def has_add_permission(self, request):
        """Failed login attempts should not be manually created."""
        return False


@admin.register(DataExportLog)
class DataExportLogAdmin(admin.ModelAdmin):
    """Admin interface for data export logs."""

    list_display = [
        "created_at",
        "user_email",
        "export_type",
        "record_count",
        "household_link",
        "file_format",
        "file_size_display",
    ]

    list_filter = [
        "export_type",
        "file_format",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "ip_address",
    ]

    readonly_fields = [
        "user",
        "export_type",
        "household",
        "record_count",
        "date_range_start",
        "date_range_end",
        "ip_address",
        "user_agent",
        "file_format",
        "file_size_bytes",
        "export_filters_formatted",
        "created_at",
        "updated_at",
    ]

    date_hierarchy = "created_at"

    def user_email(self, obj):
        """Display user email."""
        return obj.user.email if obj.user else "Unknown"

    user_email.short_description = "User"
    user_email.admin_order_field = "user__email"

    def household_link(self, obj):
        """Create admin link to household."""
        if not obj.household:
            return "-"

        try:
            url = reverse("admin:households_household_change", args=[obj.household.pk])
            return format_html('<a href="{}">{}</a>', url, obj.household.name)
        except Exception:
            return obj.household.name

    household_link.short_description = "Household"

    def file_size_display(self, obj):
        """Format file size for display."""
        if not obj.file_size_bytes:
            return "-"

        # Convert to human-readable format
        size = obj.file_size_bytes
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    file_size_display.short_description = "File Size"

    def export_filters_formatted(self, obj):
        """Format export filters JSON for display."""
        if not obj.export_filters:
            return "-"
        return format_html(
            PRE_FORMATTED_TEMPLATE, json.dumps(obj.export_filters, indent=2)
        )

    export_filters_formatted.short_description = "Applied Filters"

    def has_add_permission(self, request):
        """Export logs should not be manually created."""
        return False

    def has_change_permission(self, request, obj=None):
        """Export logs should not be modified."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Export logs should not be deleted (except by superuser)."""
        return request.user.is_superuser
