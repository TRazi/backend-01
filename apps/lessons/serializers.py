from rest_framework import serializers
from .models import FinancialLesson


class FinancialLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialLesson
        fields = [
            "id",
            "title",
            "content",
            "age_group",
            "difficulty",
            "category",
            "display_order",
            "image",
            "video_url",
            "estimated_duration",
            "is_published",
            "summary",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields  # lesson content is fully read-only
