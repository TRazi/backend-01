# apps/organisations/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.organisations.models import Organisation


@admin.register(Organisation)
class OrganisationAdmin(ModelAdmin):
    """Admin interface for Organisation model."""

    list_display = [
        "name",
        "organisation_type",
        "owner",
        "subscription_tier",
        "payment_status",
        "current_member_count",
        "max_members",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "organisation_type",
        "subscription_tier",
        "payment_status",
        "is_active",
        "created_at",
    ]

    search_fields = [
        "name",
        "contact_email",
        "owner__email",
    ]

    autocomplete_fields = ["owner"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("name", "organisation_type", "owner", "contact_email")},
        ),
        (
            "Contact Details",
            {
                "fields": ("phone_number", "address", "website"),
                "classes": ("collapse",),
            },
        ),
        (
            "Financial Settings",
            {"fields": ("default_budget_cycle", "currency", "financial_year_start")},
        ),
        (
            "Subscription & Billing",
            {
                "fields": (
                    "subscription_tier",
                    "billing_cycle",
                    "next_billing_date",
                    "subscription_amount",
                    "payment_status",
                )
            },
        ),
        ("Capacity Management", {"fields": ("is_active", "max_members")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("owner")
