# apps/categories/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from categories.models import Category


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    """Admin interface for Category model."""

    list_display = [
        "name",
        "household",
        "category_type",
        "parent",
        "is_active",
        "is_deleted",
        "is_system",
        "display_order",
    ]

    list_filter = [
        "category_type",
        "is_active",
        "is_deleted",
        "is_system",
        "is_budgetable",
        "created_at",
    ]

    search_fields = [
        "name",
        "household__name",
        "description",
    ]

    autocomplete_fields = ["household", "parent"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("household", "name", "description", "category_type")},
        ),
        ("Hierarchy", {"fields": ("parent",)}),
        ("Display", {"fields": ("icon", "color", "display_order")}),
        (
            "Settings",
            {"fields": ("is_active", "is_deleted", "is_system", "is_budgetable")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("household", "parent")
