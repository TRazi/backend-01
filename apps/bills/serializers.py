from rest_framework import serializers
from .models import Bill


class BillSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    should_send_reminder = serializers.ReadOnlyField()

    class Meta:
        model = Bill
        fields = [
            "id",
            "household",
            "name",
            "description",
            "amount",
            "due_date",
            "frequency",
            "is_recurring",
            "status",
            "paid_date",
            "transaction",
            "category",
            "account",
            "reminder_days_before",
            "auto_pay_enabled",
            "color",
            "notes",
            "next_bill",
            "is_overdue",
            "is_upcoming",
            "days_until_due",
            "should_send_reminder",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "household",
            "is_overdue",
            "is_upcoming",
            "days_until_due",
            "should_send_reminder",
            "next_bill",
            "created_at",
            "updated_at",
        ]

    def create(self, validated_data):
        """
        Automatically set household to the user's household.
        """
        user = self.context["request"].user
        validated_data["household"] = user.household
        return super().create(validated_data)
