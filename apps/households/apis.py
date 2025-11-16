# apps/households/apis.py
from rest_framework import generics, permissions
from .models import Household, Membership
from .serializers import (
    HouseholdSerializer,
    HouseholdCreateSerializer,
    MembershipSerializer,
    MembershipCreateSerializer,
)


class HouseholdListCreateApi(generics.ListCreateAPIView):
    """
    List all households the current user is associated with.
    Create a new household.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # V2 structure: user has FK household (single)
        if user.household:
            return Household.objects.filter(pk=user.household.pk)
        return Household.objects.none()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return HouseholdCreateSerializer
        return HouseholdSerializer


class HouseholdDetailApi(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a household.
    """

    queryset = Household.objects.all()
    serializer_class = HouseholdSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"


class MembershipListApi(generics.ListAPIView):
    """
    List all memberships in the current user's household.
    """

    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.household:
            return Membership.objects.none()
        return Membership.objects.filter(household=user.household)


class MembershipCreateApi(generics.CreateAPIView):
    """
    Add a user to the household (admin-only logic can be added later).
    """

    serializer_class = MembershipCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
