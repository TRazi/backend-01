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


class HouseholdCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ["name", "household_type", "budget_cycle"]

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
