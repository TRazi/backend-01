from rest_framework import serializers
from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    is_high_priority = serializers.ReadOnlyField()

    class Meta:
        model = Alert
        fields = [
            "id",
            "household",
            "alert_type",
            "priority",
            "status",
            "title",
            "message",
            "trigger_value",
            "related_budget",
            "related_bill",
            "related_account",
            "related_goal",
            "action_required",
            "action_url",
            "sent_via_email",
            "sent_via_push",
            "dismissed_at",
            "dismissed_by",
            "is_active",
            "is_high_priority",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AlertDismissSerializer(serializers.Serializer):
    """
    Used only for dismissing an alert.
    """

    def update(self, instance, validated_data):
        request = self.context["request"]
        instance.status = "dismissed"
        instance.dismissed_by = request.user
        instance.save(update_fields=["status", "dismissed_by", "updated_at"])
        return instance
