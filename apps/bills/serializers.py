from rest_framework import serializers
from .models import Bill, BillAttachment


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


class BillAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for BillAttachment model.

    Handles bill/invoice document uploads and OCR processing results.
    """

    file_url = serializers.SerializerMethodField()
    uploaded_by_name = serializers.CharField(
        source="uploaded_by.get_full_name", read_only=True, allow_null=True
    )

    class Meta:
        model = BillAttachment
        fields = [
            "id",
            "bill",
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
        """Get absolute URL for the bill document."""
        if obj.file:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class BillAttachmentUploadSerializer(serializers.ModelSerializer):
    """
    Serializer for uploading bill/invoice documents.

    Validates file size and type before upload.
    Triggers OCR processing if enabled.
    """

    class Meta:
        model = BillAttachment
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


class BillScanSerializer(serializers.Serializer):
    """
    Serializer for scanning bill/invoice images and extracting bill data.

    Accepts an image file and returns structured OCR data that can be used
    to pre-populate a bill.
    """

    image = serializers.FileField(
        required=True, help_text="Bill/invoice image to scan (JPG, PNG, or PDF)"
    )

    auto_create_bill = serializers.BooleanField(
        default=False, help_text="Automatically create bill from OCR data"
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
