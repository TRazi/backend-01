from rest_framework import serializers
from typing import Optional
from .models import Transaction, TransactionTag

# Error message constants
ERR_ACCOUNT_NOT_IN_HOUSEHOLD = "Account does not belong to your household."


class TransactionTagSerializer(serializers.ModelSerializer):
    """
    Serializer for TransactionTag model.

    Provides basic CRUD serialization for tags used to categorize transactions.
    Tags are household-scoped and can be applied to multiple transactions.
    """

    class Meta:
        model = TransactionTag
        fields = ["name", "color", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class TransactionSerializer(serializers.ModelSerializer):
    """
    Read serializer for Transaction model.

    Provides comprehensive transaction data including related tags and
    transfer information. Enforces household-level security on creation.

    Read-only Fields:
        - tags: Related transaction tags
        - is_transfer: Boolean indicating if transaction is a transfer
        - linked_transaction_id: ID of linked transfer (if applicable)
        - created_at, updated_at: Timestamps
    """

    tags = TransactionTagSerializer(many=True, read_only=True)
    is_transfer = serializers.SerializerMethodField()
    linked_transaction_id = serializers.SerializerMethodField()
    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )

    class Meta:
        model = Transaction
        fields = [
            "uuid",
            "account",
            "account_name",
            "transaction_type",
            "amount",
            "description",
            "merchant",
            "date",
            "status",
            "category",
            "category_name",
            "tags",
            "is_transfer",
            "linked_transaction_id",
            "notes",
            "transaction_source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "uuid",
            "tags",
            "is_transfer",
            "linked_transaction_id",
            "account_name",
            "category_name",
            "created_at",
            "updated_at",
        ]

    def get_is_transfer(self, obj: Transaction) -> bool:
        """Check if transaction is a transfer type."""
        return obj.transaction_type == "transfer"

    def get_linked_transaction_id(self, obj: Transaction) -> Optional[int]:
        """Get ID of linked transfer transaction if exists."""
        return obj.linked_transaction_id if obj.linked_transaction else None

    def validate_account(self, value) -> "Account":
        """Ensure account belongs to user's household."""
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
            if value.household_id != user.household_id:
                raise serializers.ValidationError(ERR_ACCOUNT_NOT_IN_HOUSEHOLD)
        return value

    def create(self, validated_data: dict) -> Transaction:
        """Create transaction with household validation."""
        user = self.context["request"].user
        account = validated_data["account"]

        # Enforce household safety
        if account.household_id != user.household_id:
            raise serializers.ValidationError({"account": ERR_ACCOUNT_NOT_IN_HOUSEHOLD})

        return super().create(validated_data)


class TransactionCreateSerializer(TransactionSerializer):
    """
    Write serializer for Transaction creation and updates.

    Extends TransactionSerializer with additional write-only fields for
    creating transactions with tags by name.

    Write-only Fields:
        - tag_names: List of tag names to apply to transaction

    Validation:
        - Amount must be positive (sign handled by transaction_type)
        - Transaction type must be valid (income/expense/transfer)
        - Account must belong to user's household
    """

    tag_names = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        write_only=True,
        help_text="List of tag names to apply to this transaction",
    )

    class Meta(TransactionSerializer.Meta):
        fields = TransactionSerializer.Meta.fields + ["tag_names"]

    def validate_amount(self, value: float) -> float:
        """Ensure amount is positive (sign determined by transaction_type)."""
        if value <= 0:
            raise serializers.ValidationError(
                "Amount must be a positive value. Transaction type determines the sign."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate transaction data comprehensively."""
        transaction_type = attrs.get("transaction_type")
        account = attrs.get("account")

        # Enforce account household
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            user = request.user
            if account and account.household_id != user.household_id:
                raise serializers.ValidationError(
                    {"account": ERR_ACCOUNT_NOT_IN_HOUSEHOLD}
                )

        # Validate transaction type
        if transaction_type not in ["income", "expense", "transfer"]:
            raise serializers.ValidationError(
                {
                    "transaction_type": "Invalid transaction type. Must be income, expense, or transfer."
                }
            )

        return attrs

    def update(self, instance: Transaction, validated_data: dict) -> Transaction:
        """Update transaction, preventing account changes."""
        # Prevent account from being changed via PATCH/PUT
        validated_data.pop("account", None)
        return super().update(instance, validated_data)


class LinkTransferSerializer(serializers.Serializer):
    """
    Serializer for creating linked transfer transactions.

    Used by the link_transfer ViewSet action to validate
    transfer destination and amount.
    """

    destination_account = serializers.IntegerField(
        required=True, help_text="ID of the destination account for transfer"
    )
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        help_text="Transfer amount (defaults to source transaction amount)",
    )
