from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import Goal, GoalProgress
from .serializers import GoalSerializer, GoalProgressSerializer
from .permissions import (
    IsGoalHouseholdMember,
    IsGoalProgressHouseholdMember,
)


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [permissions.IsAuthenticated, IsGoalHouseholdMember]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Goal.objects.all()
        return Goal.objects.filter(household=user.household)

    @action(detail=True, methods=["get"], url_path="progress")
    def progress_list(self, request, pk=None):
        """
        GET /goals/<id>/progress/
        Returns all progress entries for this goal.
        """
        goal = self.get_object()
        records = goal.progress_records.all().order_by("-date_added")
        serializer = GoalProgressSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="add-progress")
    def add_progress(self, request, pk=None):
        """
        POST /goals/<id>/add-progress/
        Add contribution to goal.
        Updates current_amount, computes milestone, etc.
        """
        goal = self.get_object()

        serializer = GoalProgressSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        progress = serializer.save(goal=goal)

        # Update goal totals
        goal.current_amount += progress.amount_added

        # Milestone check
        if goal.milestone_amount:
            earned = goal.calculate_stickers_earned()
            progress.milestone_reached = earned > goal.sticker_count
            goal.sticker_count = earned
            progress.save(update_fields=["milestone_reached"])

        goal.save(update_fields=["current_amount", "sticker_count", "updated_at"])

        return Response(
            GoalSerializer(goal).data,
            status=status.HTTP_201_CREATED,
        )


class GoalProgressViewSet(viewsets.ModelViewSet):
    serializer_class = GoalProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsGoalProgressHouseholdMember]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return GoalProgress.objects.all()
        return GoalProgress.objects.filter(goal__household=user.household)
