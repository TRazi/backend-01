from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Account
from .serializers import AccountSerializer, AccountCreateSerializer
from .permissions import IsAccountHouseholdMember


class AccountViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, IsAccountHouseholdMember]
    lookup_field = "uuid"

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Account.objects.all()

        return Account.objects.filter(household=user.household)

    def get_serializer_class(self):
        if self.action == "create":
            return AccountCreateSerializer
        if self.action in ["update", "partial_update"]:
            return AccountCreateSerializer  # no editing balance/status
        return AccountSerializer

    @action(detail=True, methods=["post"], url_path="close")
    def close_account(self, request, uuid=None):
        """
        POST /accounts/<uuid>/close/
        Mark an account as closed (exclude from totals).
        """
        account = self.get_object()

        account.include_in_totals = False
        account.save(update_fields=["include_in_totals", "updated_at"])

        return Response(AccountSerializer(account).data, status=status.HTTP_200_OK)
