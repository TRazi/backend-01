# apps/bills/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from bills.models import Bill


@admin.register(Bill)
class BillAdmin(ModelAdmin):
    """Admin interface for Bill model."""

    list_display = [
        "name",
        "household",
        "amount",
        "due_date",
        "frequency",
        "status",
        "is_recurring",
        "auto_pay_enabled",
        "days_until_due_display",
        "created_at",
    ]

    list_filter = [
        "status",
        "frequency",
        "is_recurring",
        "auto_pay_enabled",
        "due_date",
        "created_at",
    ]

    search_fields = [
        "name",
        "household__name",
        "description",
        "notes",
    ]

    autocomplete_fields = [
        "household",
        "category",
        "account",
        "transaction",
        "next_bill",
    ]

    date_hierarchy = "due_date"

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("household", "name", "description", "amount")},
        ),
        ("Schedule", {"fields": ("due_date", "frequency", "is_recurring")}),
        ("Payment Tracking", {"fields": ("status", "paid_date", "transaction")}),
        (
            "Categorization",
            {"fields": ("category", "account"), "classes": ("collapse",)},
        ),
        (
            "Reminders & Automation",
            {"fields": ("reminder_days_before", "auto_pay_enabled")},
        ),
        ("Display", {"fields": ("color",), "classes": ("collapse",)}),
        ("Recurring Bills", {"fields": ("next_bill",), "classes": ("collapse",)}),
        ("Notes", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def days_until_due_display(self, obj):
        """Display days until due."""
        days = obj.days_until_due
        if days is None:
            return "N/A"
        elif days < 0:
            return f"Overdue by {abs(days)} days"
        elif days == 0:
            return "Due today"
        else:
            return f"{days} days"

    days_until_due_display.short_description = "Days Until Due"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("household", "category", "account", "transaction")
        )
