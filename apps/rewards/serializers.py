from rest_framework import serializers
from .models import Reward


class RewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reward
        fields = [
            "id",
            "user",
            "reward_type",
            "title",
            "description",
            "icon",
            "badge_image",
            "earned_on",
            "points",
            "related_goal",
            "related_budget",
            "is_visible",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
