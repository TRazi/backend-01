from rest_framework import serializers
from .models import Organisation


class OrganisationSerializer(serializers.ModelSerializer):
    current_member_count = serializers.ReadOnlyField()
    has_capacity = serializers.ReadOnlyField()
    is_trial = serializers.ReadOnlyField()
    is_paid_up = serializers.ReadOnlyField()

    class Meta:
        model = Organisation
        fields = [
            "id",
            "name",
            "organisation_type",
            "contact_email",
            "owner",
            "phone_number",
            "address",
            "website",
            "default_budget_cycle",
            "currency",
            "financial_year_start",
            "subscription_tier",
            "billing_cycle",
            "next_billing_date",
            "subscription_amount",
            "payment_status",
            "is_active",
            "max_members",
            "current_member_count",
            "has_capacity",
            "is_trial",
            "is_paid_up",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "current_member_count",
            "has_capacity",
            "is_trial",
            "is_paid_up",
            "created_at",
            "updated_at",
        ]
