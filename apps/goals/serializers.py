from rest_framework import serializers
from django.utils import timezone
from .models import Goal, GoalProgress


class GoalProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalProgress
        fields = [
            "id",
            "goal",
            "amount_added",
            "date_added",
            "transaction",
            "notes",
            "milestone_reached",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "goal",
            "milestone_reached",
            "created_at",
            "updated_at",
        ]


class GoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    is_completed = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()
    expected_milestones = serializers.ReadOnlyField()
    total_contributed = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            "id",
            "household",
            "name",
            "description",
            "goal_type",
            "target_amount",
            "current_amount",
            "due_date",
            "status",
            "milestone_amount",
            "sticker_count",
            "auto_contribute",
            "contribution_percentage",
            "icon",
            "color",
            "image",
            "progress_percentage",
            "remaining_amount",
            "is_completed",
            "is_overdue",
            "days_remaining",
            "expected_milestones",
            "total_contributed",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "household",
            "current_amount",
            "sticker_count",
            "progress_percentage",
            "remaining_amount",
            "is_completed",
            "is_overdue",
            "days_remaining",
            "expected_milestones",
            "total_contributed",
            "created_at",
            "updated_at",
        ]

    def get_total_contributed(self, obj):
        return obj.get_total_contributed()

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["household"] = user.household
        return super().create(validated_data)

    def validate(self, attrs):
        target = attrs.get(
            "target_amount", getattr(self.instance, "target_amount", None)
        )
        due = attrs.get("due_date", getattr(self.instance, "due_date", None))

        if target is not None and target <= 0:
            raise serializers.ValidationError("target_amount must be positive.")

        if due and due < timezone.now().date():
            raise serializers.ValidationError("due_date cannot be in the past.")

        return attrs
