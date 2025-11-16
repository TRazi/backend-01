from rest_framework import serializers
from .models import Budget, BudgetItem


class BudgetItemSerializer(serializers.ModelSerializer):
    utilization_percentage = serializers.SerializerMethodField()
    remaining_amount = serializers.SerializerMethodField()

    class Meta:
        model = BudgetItem
        fields = [
            "id",
            "budget",
            "name",
            "amount",
            "category",
            "notes",
            "utilization_percentage",
            "remaining_amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "budget",
            "utilization_percentage",
            "remaining_amount",
            "created_at",
            "updated_at",
        ]

    def get_utilization_percentage(self, obj):
        return obj.get_utilization_percentage()

    def get_remaining_amount(self, obj):
        return obj.get_remaining()


class BudgetSerializer(serializers.ModelSerializer):
    items = BudgetItemSerializer(many=True, read_only=True)
    total_spent = serializers.SerializerMethodField()
    total_remaining = serializers.SerializerMethodField()
    utilization_percentage = serializers.SerializerMethodField()
    is_active = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()
    days_remaining = serializers.ReadOnlyField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "household",
            "name",
            "start_date",
            "end_date",
            "cycle_type",
            "total_amount",
            "status",
            "alert_threshold",
            "rollover_enabled",
            "notes",
            "items",
            "total_spent",
            "total_remaining",
            "utilization_percentage",
            "is_active",
            "is_expired",
            "days_remaining",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "household",
            "total_spent",
            "total_remaining",
            "utilization_percentage",
            "is_active",
            "is_expired",
            "days_remaining",
            "created_at",
            "updated_at",
        ]

    def get_total_spent(self, obj):
        return obj.get_total_spent()

    def get_total_remaining(self, obj):
        return obj.get_total_remaining()

    def get_utilization_percentage(self, obj):
        return obj.get_utilization_percentage()

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["household"] = user.household
        return super().create(validated_data)

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        total_amount = attrs.get(
            "total_amount", getattr(self.instance, "total_amount", None)
        )

        if start and end and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")

        if total_amount is not None and total_amount <= 0:
            raise serializers.ValidationError("total_amount must be positive.")

        return attrs


class BudgetItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItem
        fields = ["name", "amount", "category", "notes"]

    def create(self, validated_data):
        budget = self.context["budget"]
        validated_data["budget"] = budget
        return super().create(validated_data)
