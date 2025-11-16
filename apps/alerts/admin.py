# apps/alerts/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from alerts.models import Alert


@admin.register(Alert)
class AlertAdmin(ModelAdmin):
    """Admin interface for Alert model."""

    list_display = [
        "title_display",
        "household",
        "alert_type",
        "priority",
        "status",
        "action_required",
        "sent_via_email",
        "sent_via_push",
        "created_at",
    ]

    list_filter = [
        "alert_type",
        "priority",
        "status",
        "action_required",
        "sent_via_email",
        "sent_via_push",
        "created_at",
    ]

    search_fields = [
        "title",
        "message",
        "household__name",
    ]

    autocomplete_fields = [
        "household",
        "related_budget",
        "related_bill",
        "related_account",
        "related_goal",
        "dismissed_by",
    ]

    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Alert Information",
            {
                "fields": (
                    "household",
                    "alert_type",
                    "priority",
                    "status",
                    "title",
                    "message",
                )
            },
        ),
        ("Trigger Details", {"fields": ("trigger_value",), "classes": ("collapse",)}),
        (
            "Related Objects",
            {
                "fields": (
                    "related_budget",
                    "related_bill",
                    "related_account",
                    "related_goal",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Action", {"fields": ("action_required", "action_url")}),
        ("Notifications", {"fields": ("sent_via_email", "sent_via_push")}),
        (
            "Dismissal",
            {"fields": ("dismissed_at", "dismissed_by"), "classes": ("collapse",)},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def title_display(self, obj):
        """Display title or truncated message."""
        return obj.title if obj.title else obj.message[:50] + "..."

    title_display.short_description = "Title"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "household",
                "related_budget",
                "related_bill",
                "related_account",
                "related_goal",
                "dismissed_by",
            )
        )
