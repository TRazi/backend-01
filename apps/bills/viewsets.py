from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Bill
from .serializers import BillSerializer
from .permissions import IsBillHouseholdMember


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
