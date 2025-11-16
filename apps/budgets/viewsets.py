from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Budget, BudgetItem
from .serializers import (
    BudgetSerializer,
    BudgetItemSerializer,
    BudgetItemCreateSerializer,
)
from .permissions import IsBudgetHouseholdMember, IsBudgetItemHouseholdMember


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated, IsBudgetHouseholdMember]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Budget.objects.all()
        return Budget.objects.filter(household=user.household)

    @action(detail=True, methods=["get"], url_path="utilization")
    def utilization(self, request, pk=None):
        """
        GET /budgets/<id>/utilization/
        Returns utilization, spent, remaining, and item breakdown.
        """
        budget = self.get_object()
        serializer = self.get_serializer(budget)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request, pk=None):
        """
        POST /budgets/<id>/items/
        Create a new BudgetItem under this Budget.
        """
        budget = self.get_object()

        serializer = BudgetItemCreateSerializer(
            data=request.data,
            context={"request": request, "budget": budget},
        )
        serializer.is_valid(raise_exception=True)
        item = serializer.save()

        return Response(BudgetItemSerializer(item).data, status=status.HTTP_201_CREATED)


class BudgetItemViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetItemSerializer
    permission_classes = [permissions.IsAuthenticated, IsBudgetItemHouseholdMember]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return BudgetItem.objects.all()
        return BudgetItem.objects.filter(budget__household=user.household)

    def get_serializer_class(self):
        if self.action == "create":
            return BudgetItemCreateSerializer
        return BudgetItemSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        # For create action, if budget_id is provided in data, add budget to context
        if self.action == "create" and "budget" in self.request.data:
            budget_id = self.request.data.get("budget")
            try:
                budget = Budget.objects.get(id=budget_id)
                context["budget"] = budget
            except Budget.DoesNotExist:
                pass
        return context
