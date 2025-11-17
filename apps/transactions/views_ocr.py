"""
Async DRF Endpoints for Receipt and Bill OCR Processing

Provides REST API endpoints for uploading receipts/bills and extracting data
using AWS Textract with async processing and error handling.
"""

import logging
import hashlib
from typing import Dict, Any
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from asgiref.sync import sync_to_async
from celery import shared_task

from config.utils.ocr_service import get_textract_service
from apps.transactions.models_attachments import ReceiptAttachment, ReceiptLineItem, BillAttachment

logger = logging.getLogger(__name__)


# ============================================================================
# Serializers
# ============================================================================


class ReceiptLineItemSerializer(serializers.ModelSerializer):
    """Serializer for individual receipt line items."""

    class Meta:
        model = ReceiptLineItem
        fields = [
            "id",
            "description",
            "quantity",
            "unit_price",
            "total_price",
            "line_number",
            "confidence",
        ]
        read_only_fields = ["id", "confidence"]


class ReceiptAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for receipt attachments."""

    line_items = ReceiptLineItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = ReceiptAttachment
        fields = [
            "id",
            "image",
            "merchant_name",
            "total_amount",
            "tax_amount",
            "subtotal",
            "receipt_date",
            "payment_method",
            "status",
            "error_message",
            "confidence_scores",
            "line_items",
            "created_at",
            "transaction",
        ]
        read_only_fields = [
            "id",
            "merchant_name",
            "total_amount",
            "tax_amount",
            "subtotal",
            "receipt_date",
            "payment_method",
            "status",
            "error_message",
            "confidence_scores",
            "line_items",
            "created_at",
        ]


class ReceiptUploadSerializer(serializers.Serializer):
    """Serializer for receipt upload requests."""

    image = serializers.ImageField(required=True)
    auto_create_transaction = serializers.BooleanField(default=False, required=False)
    account_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)


class BillAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for bill attachments."""

    class Meta:
        model = BillAttachment
        fields = [
            "id",
            "image",
            "provider_name",
            "bill_type",
            "account_number",
            "amount_due",
            "due_date",
            "billing_period_start",
            "billing_period_end",
            "status",
            "error_message",
            "confidence_scores",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "provider_name",
            "bill_type",
            "account_number",
            "amount_due",
            "due_date",
            "status",
            "error_message",
            "confidence_scores",
            "created_at",
        ]


class BillUploadSerializer(serializers.Serializer):
    """Serializer for bill upload requests."""

    image = serializers.ImageField(required=True)
    auto_create_bill = serializers.BooleanField(default=False, required=False)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)


# ============================================================================
# Async Tasks (Celery)
# ============================================================================


@shared_task(bind=True, max_retries=3)
def process_receipt_async(self, receipt_id: str):
    """
    Async task to process receipt with Textract.
    
    Args:
        receipt_id: UUID of ReceiptAttachment
        
    Retries:
        Up to 3 times on failure with exponential backoff
    """
    try:
        receipt = ReceiptAttachment.objects.get(id=receipt_id)
        receipt.status = "processing"
        receipt.save(update_fields=["status"])
        
        logger.info(f"Processing receipt {receipt_id}")
        
        # Read image bytes
        image_bytes = receipt.image.read()
        
        # Get Textract service
        textract = get_textract_service()
        
        if not textract.is_enabled():
            raise ValueError("AWS Textract service is not enabled")
        
        # Extract data
        result = textract.extract_receipt_data(image_bytes)
        
        if result["success"]:
            # Update receipt with extracted data
            receipt.merchant_name = result.get("merchant_name")
            receipt.total_amount = result.get("total_amount")
            receipt.tax_amount = result.get("tax_amount")
            receipt.subtotal = result.get("subtotal")
            receipt.receipt_date = result.get("date")
            receipt.payment_method = result.get("payment_method")
            receipt.confidence_scores = result.get("confidence_scores", {})
            receipt.extracted_data = result
            receipt.merchant_normalized = result.get("merchant_normalized", False)
            receipt.status = "success"
            receipt.error_message = None
            receipt.error_code = None
            
            receipt.save()
            
            # Create line items
            for item in result.get("items", []):
                ReceiptLineItem.objects.create(
                    receipt=receipt,
                    description=item.get("description", ""),
                    quantity=item.get("quantity"),
                    total_price=item.get("amount", 0),
                    line_number=len(receipt.line_items.all()),
                    confidence=item.get("confidence", 0),
                )
            
            logger.info(f"Receipt {receipt_id} processed successfully")
            
        else:
            # Mark as failed
            receipt.status = "failed"
            receipt.error_message = result.get("error", "Unknown error")
            receipt.error_code = "TEXTRACT_ERROR"
            receipt.save()
            
            logger.error(f"Receipt {receipt_id} extraction failed: {result.get('error')}")
            
    except ReceiptAttachment.DoesNotExist:
        logger.error(f"Receipt {receipt_id} not found")
    except Exception as exc:
        logger.error(f"Error processing receipt {receipt_id}: {exc}", exc_info=True)
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def process_bill_async(self, bill_id: str):
    """
    Async task to process bill with Textract.
    
    Args:
        bill_id: UUID of BillAttachment
        
    Retries:
        Up to 3 times on failure with exponential backoff
    """
    try:
        bill = BillAttachment.objects.get(id=bill_id)
        bill.status = "processing"
        bill.save(update_fields=["status"])
        
        logger.info(f"Processing bill {bill_id}")
        
        # Read image bytes
        image_bytes = bill.image.read()
        
        # Get Textract service
        textract = get_textract_service()
        
        if not textract.is_enabled():
            raise ValueError("AWS Textract service is not enabled")
        
        # Extract data
        result = textract.extract_bill_data(image_bytes)
        
        if result["success"]:
            bill.provider_name = result.get("provider_name")
            bill.bill_type = result.get("bill_type")
            bill.account_number = result.get("account_number")
            bill.amount_due = result.get("amount_due")
            bill.due_date = result.get("due_date")
            bill.previous_balance = result.get("previous_balance")
            bill.confidence_scores = result.get("confidence_scores", {})
            bill.extracted_data = result
            bill.status = "success"
            bill.error_message = None
            bill.error_code = None
            
            bill.save()
            logger.info(f"Bill {bill_id} processed successfully")
        else:
            bill.status = "failed"
            bill.error_message = result.get("error", "Unknown error")
            bill.error_code = "TEXTRACT_ERROR"
            bill.save()
            
            logger.error(f"Bill {bill_id} extraction failed: {result.get('error')}")
            
    except BillAttachment.DoesNotExist:
        logger.error(f"Bill {bill_id} not found")
    except Exception as exc:
        logger.error(f"Error processing bill {bill_id}: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


# ============================================================================
# ViewSets
# ============================================================================


class ReceiptOCRViewSet(viewsets.ModelViewSet):
    """
    API endpoints for receipt scanning and OCR.
    
    POST /api/v1/receipts/scan/
        - Upload receipt image
        - Triggers async Textract processing
        - Returns receipt object with status
    
    GET /api/v1/receipts/{id}/
        - Retrieve receipt details
        - Includes extracted data and confidence scores
    
    GET /api/v1/receipts/
        - List user's receipts
        - Filtered by status, date range, merchant
    """

    serializer_class = ReceiptAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        """Return only receipts for the current user."""
        return ReceiptAttachment.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], serializer_class=ReceiptUploadSerializer)
    def scan(self, request):
        """
        Upload and scan a receipt.
        
        Request:
            - image: Receipt image file
            - auto_create_transaction: Auto-create transaction (optional)
            - account_id: Account for transaction (optional)
            - notes: User notes (optional)
            
        Response:
            - receipt: Receipt object with status
            - processing_id: Task ID for async processing
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_file = serializer.validated_data["image"]
        
        # Validate file
        try:
            image_bytes = image_file.read()
            
            # Calculate hash for deduplication
            file_hash = hashlib.sha256(image_bytes).hexdigest()
            
            # Check for duplicate
            existing = ReceiptAttachment.objects.filter(
                user=request.user,
                file_hash=file_hash
            ).first()
            
            if existing:
                logger.info(f"Duplicate receipt detected for user {request.user.id}")
                return Response(
                    {
                        "error": "This receipt has already been processed",
                        "receipt_id": str(existing.id),
                        "created_at": existing.created_at,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            
            # Create receipt attachment
            receipt = ReceiptAttachment.objects.create(
                user=request.user,
                image=ContentFile(image_bytes, name=image_file.name),
                file_size=len(image_bytes),
                file_hash=file_hash,
                status="pending",
            )
            
            logger.info(f"Receipt created: {receipt.id} for user {request.user.id}")
            
            # Trigger async processing
            task = process_receipt_async.delay(str(receipt.id))
            
            # Return response
            response_data = {
                "receipt": ReceiptAttachmentSerializer(receipt).data,
                "processing_id": task.id,
                "message": "Receipt uploaded. Processing started.",
            }
            
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error uploading receipt: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to upload receipt: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get current processing status of a receipt."""
        receipt = self.get_object()
        
        return Response({
            "receipt_id": str(receipt.id),
            "status": receipt.status,
            "created_at": receipt.created_at,
            "updated_at": receipt.updated_at,
            "error_message": receipt.error_message,
            "merchant_name": receipt.merchant_name,
            "total_amount": receipt.total_amount,
            "line_items_count": receipt.line_items.count(),
        })


class BillOCRViewSet(viewsets.ModelViewSet):
    """
    API endpoints for bill scanning and OCR.
    
    POST /api/v1/bills/scan/
        - Upload bill image
        - Triggers async Textract processing
    
    GET /api/v1/bills/{id}/
        - Retrieve bill details
        - Includes extracted data
    
    GET /api/v1/bills/
        - List user's bills
        - Filter by bill_type, status, date range
    """

    serializer_class = BillAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        """Return only bills for the current user."""
        return BillAttachment.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"], serializer_class=BillUploadSerializer)
    def scan(self, request):
        """
        Upload and scan a bill.
        
        Request:
            - image: Bill image file
            - auto_create_bill: Auto-create bill record (optional)
            - notes: User notes (optional)
            
        Response:
            - bill: Bill object with status
            - processing_id: Task ID for async processing
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        image_file = serializer.validated_data["image"]
        
        try:
            image_bytes = image_file.read()
            
            # Calculate hash for deduplication
            file_hash = hashlib.sha256(image_bytes).hexdigest()
            
            # Check for duplicate
            existing = BillAttachment.objects.filter(
                user=request.user,
                file_hash=file_hash
            ).first()
            
            if existing:
                logger.info(f"Duplicate bill detected for user {request.user.id}")
                return Response(
                    {
                        "error": "This bill has already been processed",
                        "bill_id": str(existing.id),
                        "created_at": existing.created_at,
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            
            # Create bill attachment
            bill = BillAttachment.objects.create(
                user=request.user,
                image=ContentFile(image_bytes, name=image_file.name),
                file_size=len(image_bytes),
                file_hash=file_hash,
                status="pending",
            )
            
            logger.info(f"Bill created: {bill.id} for user {request.user.id}")
            
            # Trigger async processing
            task = process_bill_async.delay(str(bill.id))
            
            response_data = {
                "bill": BillAttachmentSerializer(bill).data,
                "processing_id": task.id,
                "message": "Bill uploaded. Processing started.",
            }
            
            return Response(response_data, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Error uploading bill: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to upload bill: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """Get current processing status of a bill."""
        bill = self.get_object()
        
        return Response({
            "bill_id": str(bill.id),
            "status": bill.status,
            "created_at": bill.created_at,
            "updated_at": bill.updated_at,
            "error_message": bill.error_message,
            "provider_name": bill.provider_name,
            "bill_type": bill.bill_type,
            "amount_due": bill.amount_due,
        })
