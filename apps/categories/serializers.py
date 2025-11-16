from rest_framework import serializers
from .models import Category


class CategorySerializer(serializers.ModelSerializer):
    full_path = serializers.ReadOnlyField()
    transaction_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    usage_stats = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "household",
            "name",
            "description",
            "category_type",
            "parent",
            "icon",
            "color",
            "display_order",
            "is_active",
            "is_deleted",
            "is_system",
            "is_budgetable",
            "full_path",
            "transaction_count",
            "total_amount",
            "usage_stats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "household",
            "is_system",
            "full_path",
            "transaction_count",
            "total_amount",
            "usage_stats",
            "created_at",
            "updated_at",
        ]

    def get_transaction_count(self, obj):
        return obj.get_transaction_count()

    def get_total_amount(self, obj):
        return obj.get_total_amount()

    def get_usage_stats(self, obj):
        return obj.get_usage_stats()


class CategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "name",
            "description",
            "category_type",
            "parent",
            "icon",
            "color",
            "display_order",
            "is_active",
            "is_budgetable",
        ]

    def create(self, validated_data):
        user = self.context["request"].user
        validated_data["household"] = user.household
        validated_data["is_deleted"] = False
        validated_data["is_system"] = False
        return super().create(validated_data)


class CategoryUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "name",
            "description",
            "category_type",
            "parent",
            "icon",
            "color",
            "display_order",
            "is_active",
            "is_budgetable",
        ]

    def validate(self, attrs):
        """Validate category updates - prevent system category modification."""
        category = self.instance
        if category and category.is_system:
            raise serializers.ValidationError("System categories cannot be updated.")
        return attrs
