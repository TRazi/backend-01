# apps/transactions/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.transactions.models import Transaction, TransactionTag


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    """Admin interface for Transaction model."""

    list_display = [
        "description",
        "account",
        "transaction_type",
        "amount",
        "status",
        "date",
        "category",
        "created_at",
    ]

    list_filter = [
        "transaction_type",
        "status",
        "transaction_source",
        "is_recurring",
        "date",
        "created_at",
    ]

    search_fields = [
        "description",
        "merchant",
        "account__account_name",
        "account__household__name",
    ]

    autocomplete_fields = [
        "account",
        "category",
        "goal",
        "budget",
        "linked_transaction",
    ]

    date_hierarchy = "date"

    fieldsets = (
        (
            "Transaction Details",
            {"fields": ("account", "transaction_type", "status", "amount", "date")},
        ),
        ("Description", {"fields": ("description", "merchant", "notes")}),
        ("Categorization", {"fields": ("category", "tags")}),
        (
            "Links",
            {
                "fields": ("goal", "budget", "linked_transaction"),
                "classes": ("collapse",),
            },
        ),
        (
            "Entry Method",
            {
                "fields": ("transaction_source", "voice_entry_flag", "receipt_image"),
                "classes": ("collapse",),
            },
        ),
        ("Settings", {"fields": ("is_recurring",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "account", "account__household", "category", "goal", "budget"
            )
        )


@admin.register(TransactionTag)
class TransactionTagAdmin(ModelAdmin):
    """Admin interface for TransactionTag model."""

    list_display = ["name", "household", "color", "created_at"]

    list_filter = ["created_at"]

    search_fields = ["name", "household__name", "description"]

    autocomplete_fields = ["household"]

    fieldsets = (
        ("Tag Details", {"fields": ("household", "name", "color", "description")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]
