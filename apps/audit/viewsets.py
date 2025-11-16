from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import AuditLog
from .serializers import AuditLogSerializer
from .permissions import IsAuditAdmin


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Staff-only access to audit logs.
    Fully read-only. Highly sensitive.
    """

    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAuditAdmin]
    queryset = AuditLog.objects.all().order_by("-created_at")

    filter_backends = [DjangoFilterBackend, OrderingFilter, SearchFilter]
    ordering_fields = ["created_at", "action_type"]
    search_fields = ["action_type", "ip_address", "user__email"]

    filterset_fields = {
        "user": ["exact"],
        "action_type": ["exact", "icontains"],
        "created_at": ["gte", "lte"],
    }
