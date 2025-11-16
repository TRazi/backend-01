from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
import logging

from .models import Bill, BillAttachment
from .serializers import (
    BillSerializer,
    BillAttachmentSerializer,
    BillAttachmentUploadSerializer,
    BillScanSerializer,
)
from .permissions import IsBillHouseholdMember

logger = logging.getLogger("kinwise.bills")


class BillViewSet(viewsets.ModelViewSet):
    """
    FULL CRUD for Bills.
    Household-scoped.
    Includes a custom action to mark bills as paid.
    """

    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated, IsBillHouseholdMember]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Bill.objects.all()

        # Household-scoped
        return Bill.objects.filter(household=user.household)

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        """
        POST /api/v1/bills/<id>/mark-paid/
        Mark a bill as paid and optionally link a transaction.
        """
        bill = self.get_object()

        transaction = request.data.get("transaction")
        paid_date = request.data.get("paid_date") or timezone.now().date()

        bill.status = "paid"
        bill.paid_date = paid_date

        if transaction:
            bill.transaction_id = transaction

        bill.save(update_fields=["status", "paid_date", "transaction", "updated_at"])

        serializer = self.get_serializer(bill)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="upcoming")
    def upcoming_bills(self, request):
        qs = self.get_queryset().filter(status="pending")
        qs = [b for b in qs if b.is_upcoming]

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="overdue")
    def overdue_bills(self, request):
        qs = self.get_queryset().filter(status="pending")
        qs = [b for b in qs if b.is_overdue]

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="scan-bill")
    def scan_bill(self, request):
        """
        Process bill/invoice image via OCR and optionally create bill.

        Accepts a bill image, runs AWS Textract OCR, and returns structured data.
        Can automatically create a bill if requested.

        Request (multipart/form-data):
            - image: Bill/invoice image file (required)
            - auto_create_bill: Boolean (optional, default=False)

        Returns:
            200: OCR data and bill (if created)
            400: Validation errors
            503: OCR service unavailable
        """
        from config.utils.ocr_service import get_textract_service
        from django.core.exceptions import ValidationError as DjangoValidationError

        serializer = BillScanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image = serializer.validated_data["image"]
        auto_create = serializer.validated_data.get("auto_create_bill", False)

        # Get OCR service
        ocr_service = get_textract_service()

        if not ocr_service.is_enabled():
            logger.warning(
                "Bill OCR requested but service disabled",
                extra={"user_id": request.user.id},
            )
            return Response(
                {"detail": "OCR service is not currently available"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            # Read image bytes
            image_bytes = image.read()

            # Extract bill data
            ocr_result = ocr_service.extract_bill_data(image_bytes)

            if not ocr_result.get("success"):
                logger.error(
                    f"Bill OCR processing failed: {ocr_result.get('error')}",
                    extra={"user_id": request.user.id},
                )
                return Response(
                    {
                        "detail": "Failed to process bill image",
                        "error": ocr_result.get("error"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response_data = {
                "ocr_data": {
                    "provider_name": ocr_result.get("provider_name"),
                    "bill_type": ocr_result.get("bill_type"),
                    "account_number": ocr_result.get("account_number"),
                    "due_date": ocr_result.get("due_date"),
                    "amount_due": ocr_result.get("amount_due"),
                    "billing_period": ocr_result.get("billing_period"),
                    "confidence_scores": ocr_result.get("confidence_scores", {}),
                },
                "bill_created": False,
            }

            # Auto-create bill if requested
            if auto_create:
                bill_data = {
                    "household": request.user.household,
                    "name": ocr_result.get("provider_name") or "Scanned Bill",
                    "amount": abs(float(ocr_result.get("amount_due") or 0)),
                    "due_date": ocr_result.get("due_date") or timezone.now().date(),
                    "status": "pending",
                    "is_recurring": False,  # User can update if recurring
                    "description": f"Bill type: {ocr_result.get('bill_type') or 'Unknown'}",
                }

                # Add account number to notes if available
                if ocr_result.get("account_number"):
                    bill_data["notes"] = f"Account: {ocr_result.get('account_number')}"

                bill = Bill.objects.create(**bill_data)

                # Save bill image as attachment
                from django.core.files.base import ContentFile

                BillAttachment.objects.create(
                    bill=bill,
                    file=ContentFile(image_bytes, name=image.name),
                    file_name=image.name,
                    file_size=len(image_bytes),
                    file_type=image.name.split(".")[-1].lower(),
                    ocr_processed=True,
                    ocr_text=ocr_result.get("full_text", ""),
                    ocr_data=ocr_result,
                    ocr_confidence=ocr_result.get("confidence_scores", {}).get("total"),
                    ocr_processed_at=timezone.now(),
                    uploaded_by=request.user,
                )

                response_data["bill_created"] = True
                response_data["bill"] = BillSerializer(
                    bill, context={"request": request}
                ).data

                logger.info(
                    f"Bill created from OCR: {bill.id}",
                    extra={
                        "user_id": request.user.id,
                        "bill_id": bill.id,
                        "provider": ocr_result.get("provider_name"),
                        "amount": ocr_result.get("amount_due"),
                    },
                )

            return Response(response_data, status=status.HTTP_200_OK)

        except DjangoValidationError as e:
            logger.error(
                f"Validation error in bill OCR: {str(e)}",
                extra={"user_id": request.user.id},
                exc_info=True,
            )
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(
                f"Error processing bill: {str(e)}",
                extra={"user_id": request.user.id},
                exc_info=True,
            )
            return Response(
                {"detail": "Failed to process bill. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="upload-document")
    def upload_document(self, request, pk=None):
        """
        Upload a bill/invoice document for an existing bill.

        Processes the document with OCR and attaches it to the bill.

        Request (multipart/form-data):
            - file: Bill/invoice document file
            - file_name: Optional custom filename

        Returns:
            201: Attachment created with OCR data
            400: Validation errors
        """
        from config.utils.ocr_service import get_textract_service

        bill = self.get_object()

        serializer = BillAttachmentUploadSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create attachment
        attachment = serializer.save(bill=bill)

        # Process with OCR if enabled
        ocr_service = get_textract_service()
        if ocr_service.is_enabled():
            try:
                attachment.file.seek(0)
                image_bytes = attachment.file.read()

                ocr_result = ocr_service.extract_bill_data(image_bytes)

                if ocr_result.get("success"):
                    attachment.ocr_processed = True
                    attachment.ocr_data = ocr_result
                    attachment.ocr_text = ocr_result.get("full_text", "")
                    attachment.ocr_confidence = ocr_result.get(
                        "confidence_scores", {}
                    ).get("total")
                    attachment.ocr_processed_at = timezone.now()
                else:
                    attachment.ocr_error = ocr_result.get("error", "Unknown error")

                attachment.save()

                logger.info(
                    f"Bill document uploaded and processed for bill {bill.id}",
                    extra={
                        "user_id": request.user.id,
                        "bill_id": bill.id,
                        "attachment_id": attachment.id,
                    },
                )
            except Exception as e:
                logger.error(
                    f"OCR processing failed for bill attachment: {str(e)}",
                    extra={
                        "user_id": request.user.id,
                        "attachment_id": attachment.id,
                    },
                    exc_info=True,
                )
                attachment.ocr_error = str(e)
                attachment.save()

        return Response(
            BillAttachmentSerializer(attachment, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
