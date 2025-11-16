# apps/goals/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from goals.models import Goal, GoalProgress


class GoalProgressInline(TabularInline):
    """Inline for GoalProgress in Goal admin."""

    model = GoalProgress
    extra = 0
    fields = ["amount_added", "date_added", "milestone_reached", "notes"]
    readonly_fields = ["date_added"]


@admin.register(Goal)
class GoalAdmin(ModelAdmin):
    """Admin interface for Goal model."""

    list_display = [
        "name",
        "household",
        "goal_type",
        "target_amount",
        "current_amount",
        "progress",
        "due_date",
        "status",
        "sticker_count",
        "created_at",
    ]

    list_filter = [
        "status",
        "goal_type",
        "due_date",
        "auto_contribute",
        "created_at",
    ]

    search_fields = [
        "name",
        "household__name",
        "description",
    ]

    autocomplete_fields = ["household"]

    date_hierarchy = "due_date"

    inlines = [GoalProgressInline]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("household", "name", "description", "goal_type")},
        ),
        (
            "Financial Targets",
            {"fields": ("target_amount", "current_amount", "due_date")},
        ),
        (
            "Gamification",
            {"fields": ("milestone_amount", "sticker_count"), "classes": ("collapse",)},
        ),
        (
            "Auto Contribution",
            {
                "fields": ("auto_contribute", "contribution_percentage"),
                "classes": ("collapse",),
            },
        ),
        ("Display", {"fields": ("icon", "color", "image"), "classes": ("collapse",)}),
        ("Status", {"fields": ("status",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    def progress(self, obj):
        """Display progress percentage."""
        return f"{obj.progress_percentage:.1f}%"

    progress.short_description = "Progress"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("household")


@admin.register(GoalProgress)
class GoalProgressAdmin(ModelAdmin):
    """Admin interface for GoalProgress model."""

    list_display = [
        "goal",
        "amount_added",
        "date_added",
        "milestone_reached",
        "transaction",
        "created_at",
    ]

    list_filter = [
        "milestone_reached",
        "date_added",
        "created_at",
    ]

    search_fields = [
        "goal__name",
        "notes",
    ]

    autocomplete_fields = ["goal", "transaction"]

    date_hierarchy = "date_added"

    fieldsets = (
        (
            "Progress Details",
            {"fields": ("goal", "amount_added", "date_added", "milestone_reached")},
        ),
        ("Links", {"fields": ("transaction",), "classes": ("collapse",)}),
        ("Notes", {"fields": ("notes",), "classes": ("collapse",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["date_added", "created_at", "updated_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("goal", "transaction")
