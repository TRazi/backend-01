# apps/rewards/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.rewards.models import Reward


@admin.register(Reward)
class RewardAdmin(ModelAdmin):
    """Admin interface for Reward model."""

    list_display = [
        "title",
        "user",
        "reward_type",
        "points",
        "earned_on",
        "is_visible",
        "created_at",
    ]

    list_filter = [
        "reward_type",
        "is_visible",
        "earned_on",
        "created_at",
    ]

    search_fields = [
        "title",
        "description",
        "user__email",
        "user__first_name",
        "user__last_name",
    ]

    autocomplete_fields = ["user", "related_goal", "related_budget"]

    date_hierarchy = "earned_on"

    fieldsets = (
        (
            "Reward Details",
            {"fields": ("user", "reward_type", "title", "description", "points")},
        ),
        ("Display", {"fields": ("icon", "badge_image", "is_visible")}),
        (
            "Related Objects",
            {"fields": ("related_goal", "related_budget"), "classes": ("collapse",)},
        ),
        ("Dates", {"fields": ("earned_on",)}),
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
            .select_related("user", "related_goal", "related_budget")
        )
