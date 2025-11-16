from rest_framework import viewsets, permissions
from .models import Organisation
from .serializers import OrganisationSerializer
from .permissions import IsAdminOnly


class OrganisationViewSet(viewsets.ModelViewSet):
    """
    ADMIN-ONLY B2B Organisation CRUD.
    No household scoping.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOnly]
    serializer_class = OrganisationSerializer

    def get_queryset(self):
        qs = Organisation.objects.all()

        # Optional filters
        is_active = self.request.query_params.get("active")
        if is_active in ["true", "false"]:
            qs = qs.filter(is_active=(is_active == "true"))

        tier = self.request.query_params.get("subscription_tier")
        if tier:
            qs = qs.filter(subscription_tier=tier)

        payment_status = self.request.query_params.get("payment_status")
        if payment_status:
            qs = qs.filter(payment_status=payment_status)

        return qs
