from rest_framework import serializers
from typing import Optional
from django.utils import timezone
from .models import Transaction, TransactionTag, TransactionAttachment, TransactionSplit

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


class TransactionAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for TransactionAttachment model.

    Handles receipt uploads and OCR processing results.
    Provides read access to OCR data and processing status.
    """

    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.get_full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = TransactionAttachment
        fields = [
            "id",
            "transaction",
            "file",
            "file_url",
            "file_name",
            "file_size",
            "file_type",
            "ocr_processed",
            "ocr_text",
            "ocr_data",
            "ocr_confidence",
            "ocr_processed_at",
            "ocr_error",
            "uploaded_by",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "file_url",
            "ocr_processed",
            "ocr_text",
            "ocr_data",
            "ocr_confidence",
            "ocr_processed_at",
            "ocr_error",
            "uploaded_by_name",
            "created_at",
            "updated_at",
        ]

    def get_file_url(self, obj):
        """Get absolute URL for the receipt image."""
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class TransactionAttachmentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for uploading receipt images.

    Validates file size and type before upload.
    Triggers OCR processing if enabled.
    """

    class Meta:
        model = TransactionAttachment
        fields = [
            "id",
            "file",
            "file_name",
        ]
        read_only_fields = ["id"]

    def validate_file(self, value):
        """Validate uploaded file."""
        from django.conf import settings

        # Check file size
        max_size = settings.RECEIPT_MAX_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size} bytes) exceeds maximum allowed size ({max_size} bytes)"
            )

        # Check file type
        file_ext = value.name.split(".")[-1].lower()
        if file_ext not in settings.RECEIPT_ALLOWED_FORMATS:
            raise serializers.ValidationError(
                f"File type '{file_ext}' not allowed. "
                f"Allowed formats: {', '.join(settings.RECEIPT_ALLOWED_FORMATS)}"
            )

        return value

    def create(self, validated_data):
        """Create attachment with metadata."""
        file = validated_data.get("file")

        # Extract metadata
        if not validated_data.get("file_name"):
            validated_data["file_name"] = file.name

        validated_data["file_size"] = file.size
        validated_data["file_type"] = file.name.split(".")[-1].lower()

        # Set uploaded_by from request context
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            validated_data["uploaded_by"] = request.user

        return super().create(validated_data)


class ReceiptScanSerializer(serializers.Serializer):
    """
    Serializer for scanning receipt images and extracting transaction data.

    Accepts an image file and returns structured OCR data that can be used
    to pre-populate a transaction.
    """

    image = serializers.ImageField(
        required=True, help_text="Receipt image to scan (JPG, PNG, or PDF)"
    )

    auto_create_transaction = serializers.BooleanField(
        default=False, help_text="Automatically create transaction from OCR data"
    )

    account = serializers.IntegerField(
        required=False, help_text="Account ID for auto-created transaction"
    )

    def validate_image(self, value):
        """Validate image file."""
        from django.conf import settings

        # Check file size
        max_size = settings.RECEIPT_MAX_SIZE_MB * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"Image size exceeds maximum allowed size of {settings.RECEIPT_MAX_SIZE_MB}MB"
            )

        # Check file type
        file_ext = value.name.split(".")[-1].lower()
        if file_ext not in settings.RECEIPT_ALLOWED_FORMATS:
            raise serializers.ValidationError(
                f"File type '{file_ext}' not allowed. "
                f"Allowed formats: {', '.join(settings.RECEIPT_ALLOWED_FORMATS)}"
            )

        return value

    def validate(self, attrs):
        """Validate that account is provided if auto_create_transaction is True."""
        if attrs.get("auto_create_transaction") and not attrs.get("account"):
            raise serializers.ValidationError(
                {"account": "Account is required when auto_create_transaction is True"}
            )
        return attrs


class TransactionSplitSerializer(serializers.ModelSerializer):
    """
    Serializer for TransactionSplit model.

    Handles splitting transactions across multiple categories or members.
    Useful for grocery bills, shared expenses, etc.
    """

    category_name = serializers.CharField(
        source="category.name", read_only=True, allow_null=True
    )

    member_name = serializers.CharField(
        source="member.get_full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = TransactionSplit
        fields = [
            "id",
            "transaction",
            "category",
            "category_name",
            "amount",
            "description",
            "member",
            "member_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "category_name",
            "member_name",
            "created_at",
            "updated_at",
        ]

    def validate_amount(self, value):
        """Ensure amount is not zero."""
        if value == 0:
            raise serializers.ValidationError("Split amount cannot be zero")
        return value
