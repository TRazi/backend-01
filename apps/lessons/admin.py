# apps/lessons/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from lessons.models import FinancialLesson


@admin.register(FinancialLesson)
class FinancialLessonAdmin(ModelAdmin):
    """Admin interface for FinancialLesson model."""

    list_display = [
        "title",
        "age_group",
        "difficulty",
        "category",
        "estimated_duration",
        "is_published",
        "display_order",
        "created_at",
    ]

    list_filter = [
        "age_group",
        "difficulty",
        "is_published",
        "category",
        "created_at",
    ]

    search_fields = [
        "title",
        "content",
        "summary",
        "tags",
        "category",
    ]

    list_editable = ["display_order", "is_published"]

    fieldsets = (
        ("Basic Information", {"fields": ("title", "summary", "content")}),
        ("Classification", {"fields": ("age_group", "difficulty", "category", "tags")}),
        ("Multimedia", {"fields": ("image", "video_url"), "classes": ("collapse",)}),
        (
            "Settings",
            {"fields": ("estimated_duration", "display_order", "is_published")},
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]
