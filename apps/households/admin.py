# apps/households/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from households.models import Household, Membership


class MembershipInline(TabularInline):
    """Inline for Memberships in Household admin."""

    model = Membership
    extra = 0
    fields = ["user", "role", "membership_type", "status", "is_primary", "start_date"]
    readonly_fields = ["start_date"]
    autocomplete_fields = ["user"]


@admin.register(Household)
class HouseholdAdmin(ModelAdmin):
    """Admin interface for Household model."""

    list_display = [
        "name",
        "household_type",
        "budget_cycle",
        "member_count",
        "created_at",
    ]

    list_filter = [
        "household_type",
        "budget_cycle",
        "created_at",
    ]

    search_fields = ["name"]

    inlines = [MembershipInline]

    fieldsets = (
        ("Basic Information", {"fields": ("name", "household_type", "budget_cycle")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def member_count(self, obj):
        return obj.memberships.filter(status="active").count()

    member_count.short_description = "Active Members"


@admin.register(Membership)
class MembershipAdmin(ModelAdmin):
    """Admin interface for Membership model."""

    list_display = [
        "user",
        "household",
        "membership_type",
        "role",
        "status",
        "is_primary",
        "start_date",
    ]

    list_filter = [
        "membership_type",
        "role",
        "status",
        "is_primary",
        "start_date",
    ]

    search_fields = [
        "user__email",
        "household__name",
    ]

    autocomplete_fields = ["user", "household", "organisation"]

    fieldsets = (
        (
            "Membership Details",
            {"fields": ("user", "household", "organisation", "is_primary")},
        ),
        (
            "Subscription & Permissions",
            {"fields": ("membership_type", "role", "status")},
        ),
        ("Dates", {"fields": ("start_date", "end_date")}),
        (
            "Billing (Optional)",
            {
                "fields": (
                    "billing_cycle",
                    "next_billing_date",
                    "amount",
                    "payment_status",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["start_date", "created_at", "updated_at"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user", "household", "organisation")
        )
