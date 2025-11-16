from decimal import Decimal
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction as db_transaction
from django.utils import timezone
import logging

from .models import Transaction, TransactionTag, TransactionAttachment, TransactionSplit
from .serializers import (
    TransactionSerializer,
    TransactionCreateSerializer,
    TransactionTagSerializer,
    LinkTransferSerializer,
    TransactionAttachmentSerializer,
    TransactionAttachmentUploadSerializer,
    ReceiptScanSerializer,
    TransactionSplitSerializer,
    TransactionSplitCreateSerializer,
    BulkSplitSerializer,
)
from .permissions import IsTransactionHouseholdMember

logger = logging.getLogger("kinwise.transactions")


class TransactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing household transactions.

    Provides full CRUD operations for transactions with automatic household scoping.
    All transactions are filtered to the authenticated user's household.

    Features:
        - Automatic household scoping for data isolation
        - Custom actions for transfers, tagging, OCR, and voice input
        - Comprehensive filtering and search capabilities
        - Audit logging for all operations

    Filters:
        - account: Filter by account ID
        - transaction_type: Filter by type (income/expense/transfer)
        - status: Filter by status (pending/completed/failed/cancelled)
        - category: Filter by category ID
        - search: Search in description, merchant, and notes

    Ordering:
        - Default: -date (newest first)
        - Available: date, amount, created_at, merchant

    Custom Actions:
        - link_transfer: Create linked transfer transaction
        - add_tags: Add tags to transaction by name
        - remove_tag: Remove tag from transaction
        - receipt_ocr: Upload and process receipt image (stub)
        - voice_input: Create transaction via voice (stub)

    Permissions:
        - IsAuthenticated: User must be authenticated
        - IsTransactionHouseholdMember: User must belong to transaction's household
    """

    permission_classes = [permissions.IsAuthenticated, IsTransactionHouseholdMember]
    lookup_field = "uuid"
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["account", "transaction_type", "status", "category"]
    search_fields = ["description", "merchant", "notes"]
    ordering_fields = ["date", "amount", "created_at", "merchant"]
    ordering = ["-date"]

    def get_queryset(self):
        """
        Return transactions for authenticated user's household.

        Staff users can see all transactions for administrative purposes.
        Regular users only see transactions from their household accounts.

        Optimizations:
            - select_related for account and category (reduce queries)
            - prefetch_related for tags (optimize M2M)
        """
        user = self.request.user
        if user.is_staff:
            return Transaction.objects.select_related("account", "category").all()

        return (
            Transaction.objects.filter(account__household=user.household)
            .select_related("account", "category")
            .prefetch_related("tags")
        )

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ["create", "update", "partial_update"]:
            return TransactionCreateSerializer
        return TransactionSerializer

    def perform_create(self, serializer):
        """Create transaction with audit logging."""
        transaction = serializer.save()
        logger.info(
            f"Transaction created: {transaction.id} by user {self.request.user.id}",
            extra={
                "user_id": self.request.user.id,
                "household_id": self.request.user.household_id,
                "transaction_id": transaction.id,
                "amount": float(transaction.amount),
                "type": transaction.transaction_type,
            },
        )

    def perform_update(self, serializer):
        """Update transaction with audit logging."""
        transaction = serializer.save()
        logger.info(
            f"Transaction updated: {transaction.id} by user {self.request.user.id}",
            extra={
                "user_id": self.request.user.id,
                "transaction_id": transaction.id,
            },
        )

    def perform_destroy(self, instance):
        """Delete transaction with audit logging."""
        logger.warning(
            f"Transaction deleted: {instance.id} by user {self.request.user.id}",
            extra={
                "user_id": self.request.user.id,
                "household_id": self.request.user.household_id,
                "transaction_id": instance.id,
                "amount": float(instance.amount),
            },
        )
        instance.delete()

    @action(detail=True, methods=["post"], url_path="link-transfer")
    def link_transfer(self, request, pk=None):
        """
        Create linked transfer transaction.

        Creates the opposite side of a transfer transaction between accounts
        within the same household. Ensures both sides of the transfer are tracked.

        Request Body:
            {
                "destination_account": 123,  // Required: Target account ID
                "amount": "100.00"  // Optional: Defaults to source amount
            }

        Returns:
            201: Created linked transaction data
            400: Validation errors (invalid account, missing fields)
            404: Source transaction not found
            500: Server error during creation

        Example:
            POST /api/v1/transactions/456/link-transfer/
            {
                "destination_account": 789,
                "amount": "50.00"
            }
        """
        try:
            source = self.get_object()
            serializer = LinkTransferSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            dest_account_id = serializer.validated_data["destination_account"]
            amount = serializer.validated_data.get("amount", source.amount)

            # Validate destination account belongs to same household
            from accounts.models import Account

            try:
                dest_account = Account.objects.get(
                    id=dest_account_id, household=source.account.household
                )
            except Account.DoesNotExist:
                logger.warning(
                    f"Transfer link failed: account {dest_account_id} not found",
                    extra={"user_id": request.user.id, "source_id": source.id},
                )
                return Response(
                    {"detail": "Destination account not found in your household."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            with db_transaction.atomic():
                linked = Transaction.objects.create(
                    account=dest_account,
                    transaction_type=(
                        "income" if source.transaction_type == "expense" else "expense"
                    ),
                    amount=amount,
                    description=f"Transfer from {source.account.name}",
                    date=source.date,
                    status="completed",
                    category=None,
                )

                source.linked_transaction = linked
                source.save(update_fields=["linked_transaction", "updated_at"])

            logger.info(
                f"Transfer linked: {source.id} -> {linked.id}",
                extra={
                    "user_id": request.user.id,
                    "source_id": source.id,
                    "linked_id": linked.id,
                },
            )

            return Response(
                TransactionSerializer(linked, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(
                f"Error linking transfer: {str(e)}",
                extra={"user_id": request.user.id, "transaction_id": pk},
                exc_info=True,
            )
            return Response(
                {"detail": "Failed to create linked transfer. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="tags")
    def add_tags(self, request, pk=None):
        """
        Add tags to transaction by name.

        Creates tags if they don't exist in the household.
        Multiple tags can be added in a single request.

        Request Body:
            {
                "tags": ["groceries", "weekly-shopping", "essential"]
            }

        Returns:
            200: Updated transaction with tags
            400: Invalid tag data
        """
        transaction = self.get_object()
        tags = request.data.get("tags", [])

        if not isinstance(tags, list):
            return Response(
                {"detail": "Tags must be a list of strings."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for name in tags:
            tag, _ = TransactionTag.objects.get_or_create(
                name=name, household=transaction.account.household
            )
            transaction.tags.add(tag)

        logger.info(
            f"Tags added to transaction {transaction.id}: {tags}",
            extra={"user_id": request.user.id, "transaction_id": transaction.id},
        )

        return Response(
            TransactionSerializer(transaction, context={"request": request}).data
        )

    @action(detail=True, methods=["post"], url_path="remove-tag")
    def remove_tag(self, request, pk=None):
        """
        Remove tag from transaction.

        Request Body:
            {
                "tag_id": 123
            }

        Returns:
            200: Updated transaction
            400: Missing or invalid tag_id
        """
        transaction = self.get_object()
        tag_id = request.data.get("tag_id")

        if not tag_id:
            return Response(
                {"detail": "tag_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            transaction.tags.remove(tag_id)
            logger.info(
                f"Tag {tag_id} removed from transaction {transaction.id}",
                extra={"user_id": request.user.id, "transaction_id": transaction.id},
            )
        except Exception as e:
            logger.warning(
                f"Failed to remove tag: {str(e)}",
                extra={"user_id": request.user.id, "transaction_id": transaction.id},
            )

        return Response(
            TransactionSerializer(transaction, context={"request": request}).data
        )

    @action(detail=False, methods=["post"], url_path="receipt-ocr")
    def receipt_ocr(self, request):
        """
        Process receipt image via OCR and optionally create transaction.

        Accepts a receipt image, runs AWS Textract OCR, and returns structured data.
        Can automatically create a transaction if requested.

        Request (multipart/form-data):
            - image: Receipt image file (required)
            - auto_create_transaction: Boolean (optional, default=False)
            - account: Account ID (required if auto_create_transaction=True)

        Returns:
            200: OCR data and transaction (if created)
            400: Validation errors
            503: OCR service unavailable
        """
        from config.utils.ocr_service import get_textract_service
        from django.core.exceptions import ValidationError as DjangoValidationError

        serializer = ReceiptScanSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        image = serializer.validated_data["image"]
        auto_create = serializer.validated_data.get("auto_create_transaction", False)
        account_id = serializer.validated_data.get("account")

        # Get OCR service
        ocr_service = get_textract_service()

        if not ocr_service.is_enabled():
            logger.warning(
                "OCR requested but service disabled", extra={"user_id": request.user.id}
            )
            return Response(
                {"detail": "OCR service is not currently available"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            # Read image bytes
            image_bytes = image.read()

            # Extract receipt data
            ocr_result = ocr_service.extract_receipt_data(image_bytes)

            if not ocr_result.get("success"):
                logger.error(
                    f"OCR processing failed: {ocr_result.get('error')}",
                    extra={"user_id": request.user.id},
                )
                return Response(
                    {
                        "detail": "Failed to process receipt image",
                        "error": ocr_result.get("error"),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            response_data = {
                "ocr_data": {
                    "merchant_name": ocr_result.get("merchant_name"),
                    "total_amount": ocr_result.get("total_amount"),
                    "date": ocr_result.get("date"),
                    "tax_amount": ocr_result.get("tax_amount"),
                    "items": ocr_result.get("items", []),
                    "confidence_scores": ocr_result.get("confidence_scores", {}),
                },
                "transaction_created": False,
            }

            # Auto-create transaction if requested
            if auto_create and account_id:
                from accounts.models import Account

                try:
                    account = Account.objects.get(
                        id=account_id, household=request.user.household
                    )
                except Account.DoesNotExist:
                    return Response(
                        {"detail": "Account not found in your household"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create transaction from OCR data
                transaction_data = {
                    "account": account,
                    "transaction_type": "expense",
                    "amount": abs(float(ocr_result.get("total_amount") or 0)),
                    "description": ocr_result.get("merchant_name") or "Receipt scan",
                    "merchant": ocr_result.get("merchant_name") or "",
                    "date": ocr_result.get("date") or timezone.now(),
                    "transaction_source": "receipt_ocr",
                    "status": "pending",  # User can review and confirm
                }

                transaction = Transaction.objects.create(**transaction_data)

                # Save receipt image as attachment
                from django.core.files.base import ContentFile

                TransactionAttachment.objects.create(
                    transaction=transaction,
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

                response_data["transaction_created"] = True
                response_data["transaction"] = TransactionSerializer(
                    transaction, context={"request": request}
                ).data

                logger.info(
                    f"Transaction created from OCR: {transaction.id}",
                    extra={
                        "user_id": request.user.id,
                        "transaction_id": transaction.id,
                        "merchant": ocr_result.get("merchant_name"),
                        "amount": ocr_result.get("total_amount"),
                    },
                )

            return Response(response_data, status=status.HTTP_200_OK)

        except DjangoValidationError as e:
            logger.error(
                f"Validation error in OCR: {str(e)}",
                extra={"user_id": request.user.id},
                exc_info=True,
            )
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            logger.error(
                f"Error processing receipt: {str(e)}",
                extra={"user_id": request.user.id},
                exc_info=True,
            )
            return Response(
                {"detail": "Failed to process receipt. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"], url_path="upload-receipt")
    def upload_receipt(self, request, uuid=None):
        """
        Upload a receipt image for an existing transaction.

        Processes the image with OCR and attaches it to the transaction.

        Request (multipart/form-data):
            - file: Receipt image file
            - file_name: Optional custom filename

        Returns:
            201: Attachment created with OCR data
            400: Validation errors
        """
        from config.utils.ocr_service import get_textract_service

        transaction = self.get_object()

        serializer = TransactionAttachmentUploadSerializer(
            data=request.data, context={"request": request}
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create attachment
        attachment = serializer.save(transaction=transaction)

        # Process with OCR if enabled
        ocr_service = get_textract_service()
        if ocr_service.is_enabled():
            try:
                attachment.file.seek(0)
                image_bytes = attachment.file.read()

                ocr_result = ocr_service.extract_receipt_data(image_bytes)

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
                    f"Receipt uploaded and processed for transaction {transaction.id}",
                    extra={
                        "user_id": request.user.id,
                        "transaction_id": transaction.id,
                        "attachment_id": attachment.id,
                    },
                )
            except Exception as e:
                logger.error(
                    f"OCR processing failed for attachment: {str(e)}",
                    extra={
                        "user_id": request.user.id,
                        "attachment_id": attachment.id,
                    },
                    exc_info=True,
                )
                attachment.ocr_error = str(e)
                attachment.save()

        return Response(
            TransactionAttachmentSerializer(
                attachment, context={"request": request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"], url_path="voice")
    def voice_input(self, request):
        """
        Create transaction via voice input.

        Future implementation will integrate voice parsing to extract:
        - Transaction type
        - Amount
        - Description/merchant
        - Category

        Returns:
            200: Placeholder response
        """
        # FUTURE: Voice parsing service integration for hands-free transaction entry
        logger.info("Voice input requested (stub)", extra={"user_id": request.user.id})
        return Response(
            {"message": "Voice processing placeholder - coming soon"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"], url_path="splits")
    def splits(self, request, uuid=None):
        """
        Manage transaction splits.

        GET: List all splits for this transaction
        POST: Create a new split

        Request Body (POST):
            {
                "category": 123,  // Optional: Category ID
                "amount": "50.00",  // Required: Split amount
                "description": "My share of groceries",  // Optional
                "member": 456  // Optional: Assign to specific member
            }

        Returns:
            GET 200: List of splits with totals
            POST 201: Created split
            POST 400: Validation errors
        """
        from django.db.models import Sum

        transaction = self.get_object()

        if request.method == "GET":
            splits = TransactionSplit.objects.filter(
                transaction=transaction
            ).select_related("category", "member")

            total_split = (
                splits.aggregate(total=Sum("amount"))["total"] or 0
            )
            remaining = abs(transaction.amount) - abs(total_split)

            serializer = TransactionSplitSerializer(
                splits, many=True, context={"request": request}
            )

            return Response(
                {
                    "count": splits.count(),
                    "total_split": total_split,
                    "remaining": remaining,
                    "splits": serializer.data,
                }
            )

        elif request.method == "POST":
            serializer = TransactionSplitCreateSerializer(
                data=request.data,
                context={"request": request, "transaction": transaction},
            )

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            split = serializer.save(transaction=transaction)

            logger.info(
                f"Split created for transaction {transaction.id}: ${split.amount}",
                extra={
                    "user_id": request.user.id,
                    "transaction_id": transaction.id,
                    "split_id": split.id,
                    "amount": float(split.amount),
                },
            )

            return Response(
                TransactionSplitSerializer(split, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )

    @action(detail=True, methods=["post"], url_path="split-equally")
    def split_equally(self, request, uuid=None):
        """
        Split transaction equally or proportionally across household members.

        Convenience endpoint for common use case: splitting bills equally
        among flatmates or family members.

        Request Body:
            {
                "members": [123, 456, 789],  // User IDs to split between
                "split_type": "equal"  // or "proportional"
                "proportions": {  // Required if split_type=proportional
                    "123": 70.00,
                    "456": 30.00
                }
            }

        Example (Equal Split):
            POST /api/v1/transactions/{uuid}/split-equally/
            {
                "members": [1, 2, 3],
                "split_type": "equal"
            }

            Result: $300 bill → $100 per person

        Example (Proportional Split - DINK 70/30):
            POST /api/v1/transactions/{uuid}/split-equally/
            {
                "members": [1, 2],
                "split_type": "proportional",
                "proportions": {
                    "1": 70.00,
                    "2": 30.00
                }
            }

            Result: $1000 rent → $700 (person 1), $300 (person 2)

        Returns:
            201: Created splits
            400: Validation errors
        """
        from users.models import User

        transaction = self.get_object()
        serializer = BulkSplitSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member_ids = serializer.validated_data["members"]
        split_type = serializer.validated_data.get("split_type", "equal")
        proportions = serializer.validated_data.get("proportions", {})

        # Validate members belong to household
        members = User.objects.filter(
            id__in=member_ids, household=transaction.account.household
        )

        if members.count() != len(member_ids):
            return Response(
                {"detail": "All members must belong to transaction's household"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete existing splits (fresh start)
        TransactionSplit.objects.filter(transaction=transaction).delete()

        # Calculate split amounts
        splits_created = []

        with db_transaction.atomic():
            if split_type == "equal":
                # Equal split
                split_amount = abs(transaction.amount) / len(members)

                for member in members:
                    split = TransactionSplit.objects.create(
                        transaction=transaction,
                        member=member,
                        amount=split_amount,
                        description=f"{member.get_full_name()}'s share (equal split)",
                        category=transaction.category,
                    )
                    splits_created.append(split)

            else:  # proportional
                # Proportional split (e.g., 70/30 for DINK couples)
                for member in members:
                    percentage = proportions.get(str(member.id), 0)
                    split_amount = abs(transaction.amount) * (Decimal(str(percentage)) / Decimal('100'))

                    split = TransactionSplit.objects.create(
                        transaction=transaction,
                        member=member,
                        amount=split_amount,
                        description=f"{member.get_full_name()}'s share ({percentage}%)",
                        category=transaction.category,
                    )
                    splits_created.append(split)

        logger.info(
            f"Transaction {transaction.id} split {split_type} "
            f"across {len(members)} members",
            extra={
                "user_id": request.user.id,
                "transaction_id": transaction.id,
                "split_type": split_type,
                "member_count": len(members),
            },
        )

        return Response(
            {
                "message": f"Transaction split {split_type} across {len(members)} members",
                "splits": TransactionSplitSerializer(
                    splits_created, many=True, context={"request": request}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path="splits/(?P<split_id>[0-9]+)",
    )
    def delete_split(self, request, uuid=None, split_id=None):
        """
        Delete a specific split.

        DELETE /api/v1/transactions/{uuid}/splits/{split_id}/

        Returns:
            204: Split deleted
            404: Split not found
        """
        transaction = self.get_object()

        try:
            split = TransactionSplit.objects.get(id=split_id, transaction=transaction)
            split.delete()

            logger.info(
                f"Split {split_id} deleted from transaction {transaction.id}",
                extra={
                    "user_id": request.user.id,
                    "transaction_id": transaction.id,
                    "split_id": split_id,
                },
            )

            return Response(status=status.HTTP_204_NO_CONTENT)

        except TransactionSplit.DoesNotExist:
            return Response(
                {"detail": "Split not found"}, status=status.HTTP_404_NOT_FOUND
            )
