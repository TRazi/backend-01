# apps/budgets/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from budgets.models import Budget, BudgetItem


class BudgetItemInline(TabularInline):
    """Inline for BudgetItems in Budget admin."""

    model = BudgetItem
    extra = 1
    fields = ["name", "amount", "category", "notes"]
    autocomplete_fields = ["category"]


@admin.register(Budget)
class BudgetAdmin(ModelAdmin):
    """Admin interface for Budget model."""

    list_display = [
        "name",
        "household",
        "total_amount",
        "start_date",
        "end_date",
        "cycle_type",
        "status",
        "utilization",
        "created_at",
    ]

    list_filter = [
        "status",
        "cycle_type",
        "start_date",
        "end_date",
        "created_at",
    ]

    search_fields = [
        "name",
        "household__name",
        "notes",
    ]

    autocomplete_fields = ["household"]

    date_hierarchy = "start_date"

    inlines = [BudgetItemInline]

    fieldsets = (
        ("Basic Information", {"fields": ("household", "name", "total_amount")}),
        ("Period", {"fields": ("start_date", "end_date", "cycle_type")}),
        (
            "Status & Settings",
            {"fields": ("status", "alert_threshold", "rollover_enabled")},
        ),
        ("Notes", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def utilization(self, obj):
        """Display budget utilization percentage."""
        percentage = obj.get_utilization_percentage()
        return f"{percentage:.1f}%"

    utilization.short_description = "Utilization"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("household")


@admin.register(BudgetItem)
class BudgetItemAdmin(ModelAdmin):
    """Admin interface for BudgetItem model."""

    list_display = [
        "name",
        "budget",
        "amount",
        "category",
        "spent",
        "remaining",
        "created_at",
    ]

    list_filter = [
        "budget__household",
        "category",
        "created_at",
    ]

    search_fields = [
        "name",
        "budget__name",
        "category__name",
        "notes",
    ]

    autocomplete_fields = ["budget", "category"]

    fieldsets = (
        ("Budget Item Details", {"fields": ("budget", "name", "amount", "category")}),
        ("Notes", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def spent(self, obj):
        """Display amount spent."""
        return f"${obj.get_spent():.2f}"

    spent.short_description = "Spent"

    def remaining(self, obj):
        """Display remaining amount."""
        return f"${obj.get_remaining():.2f}"

    remaining.short_description = "Remaining"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("budget", "category")
