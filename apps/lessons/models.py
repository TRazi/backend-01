# apps/lessons/models.py
from django.db import models

from apps.common.models import BaseModel
from apps.lessons.enums import AGE_GROUP_CHOICES, LESSON_DIFFICULTY_CHOICES


class FinancialLesson(BaseModel):
    """
    Represents educational financial literacy content.

    Key features:
    - Age-appropriate content
    - Educational topics (budgeting, saving, investing)
    - Multimedia support (text, images, videos)
    - Progress tracking per user

    Examples:
    - "What is a Budget?" (age_group: child)
    - "Understanding Credit Scores" (age_group: young_adult)
    - "Investment Basics" (age_group: adult)
    """

    title = models.CharField(max_length=255, help_text="Lesson title")

    content = models.TextField(help_text="Lesson content (supports markdown)")

    age_group = models.CharField(
        max_length=20,
        choices=AGE_GROUP_CHOICES,
        default="all",
        help_text="Target age group for this lesson",
    )

    difficulty = models.CharField(
        max_length=20,
        choices=LESSON_DIFFICULTY_CHOICES,
        default="beginner",
        help_text="Lesson difficulty level",
    )

    # Organization
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Lesson category (e.g., 'Budgeting', 'Saving', 'Investing')",
    )

    display_order = models.PositiveIntegerField(
        default=0, help_text="Order for displaying lessons"
    )

    # Multimedia
    image = models.ImageField(
        upload_to="lessons/images/",
        null=True,
        blank=True,
        help_text="Optional lesson image",
    )

    video_url = models.URLField(
        blank=True, help_text="Optional video URL (YouTube, Vimeo, etc.)"
    )

    # Duration and status
    estimated_duration = models.PositiveIntegerField(
        default=5, help_text="Estimated minutes to complete lesson"
    )

    is_published = models.BooleanField(
        default=False, help_text="Whether this lesson is published and visible"
    )

    # SEO and metadata
    summary = models.TextField(blank=True, help_text="Short summary for lesson preview")

    tags = models.CharField(
        max_length=255, blank=True, help_text="Comma-separated tags for search"
    )

    class Meta:
        db_table = "financial_lessons"
        verbose_name = "Financial Lesson"
        verbose_name_plural = "Financial Lessons"
        indexes = [
            models.Index(fields=["age_group", "is_published"]),
            models.Index(fields=["category", "display_order"]),
            models.Index(fields=["is_published", "display_order"]),
        ]
        ordering = ["display_order", "title"]

    def __str__(self):
        return f"{self.title} ({self.get_age_group_display()})"
