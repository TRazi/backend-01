from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone

from .models import Alert
from .serializers import AlertSerializer, AlertDismissSerializer
from .permissions import IsAlertHouseholdMember


class AlertListView(generics.ListAPIView):
    """
    Limited CRUD: Only list alerts for the user's household.
    """

    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            return Alert.objects.all()

        return Alert.objects.filter(household=user.household)


class AlertDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific alert.
    """

    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsAlertHouseholdMember]
    queryset = Alert.objects.all()


class AlertDismissView(generics.UpdateAPIView):
    """
    Dismiss a specific alert.
    Equivalent to: PATCH /alerts/<id>/dismiss/
    """

    serializer_class = AlertDismissSerializer
    permission_classes = [permissions.IsAuthenticated, IsAlertHouseholdMember]
    queryset = Alert.objects.filter(status="active")

    def patch(self, request, *args, **kwargs):
        alert = self.get_object()

        serializer = self.get_serializer(
            alert, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(AlertSerializer(alert).data)
