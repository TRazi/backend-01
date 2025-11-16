from rest_framework import serializers
from .models import Account


class AccountSerializer(serializers.ModelSerializer):
    balance = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    is_low_balance = serializers.ReadOnlyField()
    account_display_name = serializers.ReadOnlyField()

    class Meta:
        model = Account
        fields = [
            "uuid",
            "name",
            "account_type",
            "institution",
            "balance",
            "currency",
            "created_at",
            "updated_at",
            "is_active",
            "is_low_balance",
            "account_display_name",
        ]
        read_only_fields = [
            "uuid",
            "balance",
            "created_at",
            "updated_at",
            "is_active",
            "is_low_balance",
            "account_display_name",
        ]


class AccountCreateSerializer(serializers.ModelSerializer):
    """
    Create serializer allows setting only user-facing fields.
    """

    class Meta:
        model = Account
        fields = [
            "name",
            "account_type",
            "institution",
            "currency",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["household"] = user.household
        return super().create(validated_data)
