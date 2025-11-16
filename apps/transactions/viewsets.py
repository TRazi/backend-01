from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction as db_transaction
from django.utils import timezone
import logging

from .models import Transaction, TransactionTag
from .serializers import (
    TransactionSerializer,
    TransactionCreateSerializer,
    TransactionTagSerializer,
    LinkTransferSerializer,
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
        Process receipt image via OCR.

        Future implementation will integrate OCR service to extract:
        - Merchant name
        - Amount
        - Date
        - Line items

        Returns:
            200: Placeholder response
        """
        # FUTURE: OCR service integration for automatic receipt data extraction
        logger.info("Receipt OCR requested (stub)", extra={"user_id": request.user.id})
        return Response(
            {"message": "OCR processing placeholder - coming soon"},
            status=status.HTTP_200_OK,
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
