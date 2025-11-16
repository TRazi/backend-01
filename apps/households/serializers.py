# apps/households/serializers.py
from rest_framework import serializers
from .models import Household, Membership


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = [
            "uuid",
            "name",
            "household_type",
            "budget_cycle",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["uuid", "created_at", "updated_at"]
        extra_kwargs = {
            "household_type": {"required": True, "allow_blank": False},
            "budget_cycle": {"required": True, "allow_blank": False},
        }

    def validate_name(self, value):
        """Ensure household name is not empty or just whitespace."""
        if not value or not value.strip():
            raise serializers.ValidationError("Household name cannot be blank.")
        return value.strip()

    def validate_household_type(self, value):
        """Ensure household type is not empty."""
        if not value:
            raise serializers.ValidationError("Household type must be selected.")
        return value

    def validate_budget_cycle(self, value):
        """Ensure budget cycle is not empty."""
        if not value:
            raise serializers.ValidationError("Budget cycle must be selected.")
        return value


class HouseholdCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["name", "household_type", "budget_cycle"]
        extra_kwargs = {
            "household_type": {"required": True, "allow_blank": False},
            "budget_cycle": {"required": True, "allow_blank": False},
        }

    def validate_name(self, value):
        """Ensure household name is not empty or just whitespace."""
        if not value or not value.strip():
            raise serializers.ValidationError("Household name cannot be blank.")
        return value.strip()

    def validate_household_type(self, value):
        """Ensure household type is not empty."""
        if not value:
            raise serializers.ValidationError("Household type must be selected.")
        return value

    def validate_budget_cycle(self, value):
        """Ensure budget cycle is not empty."""
        if not value:
            raise serializers.ValidationError("Budget cycle must be selected.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user

        household = Household.objects.create(**validated_data)

        # Create membership record for the creator
        Membership.objects.create(
            household=household,
            user=user,
            role="admin",  # Or whatever roles your enums define
        )

        # Assign the creator's household FK
        user.household = household
        user.save(update_fields=["household"])

        return household


class MembershipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = [
            "id",
            "user",
            "household",
            "role",
            "created_at",
        ]


class MembershipCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Membership
        fields = ["user", "household", "role"]
