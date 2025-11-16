# apps/accounts/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from accounts.models import Account


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    """Admin interface for Account model."""

    list_display = [
        "name",
        "household",
        "account_type",
        "balance",
        "currency",
        "include_in_totals",
        "created_at",
    ]

    list_filter = [
        "account_type",
        "include_in_totals",
        "currency",
        "created_at",
    ]

    search_fields = [
        "name",
        "household__name",
        "institution",
    ]

    autocomplete_fields = ["household"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "household",
                    "name",
                    "account_type",
                    "institution",
                )
            },
        ),
        (
            "Balance & Credit",
            {
                "fields": (
                    "balance",
                    "currency",
                    "available_credit",
                    "credit_limit",
                )
            },
        ),
        (
            "Settings",
            {"fields": ("include_in_totals",)},
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("household")
