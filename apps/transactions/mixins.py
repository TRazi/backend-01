"""
Audit logging mixins for DRF views.
"""

from rest_framework import status
from rest_framework.response import Response

from apps.audit.services import log_model_change


class AuditLoggingMixin:
    """
    Mixin to add automatic audit logging to DRF viewsets.
    """

    def perform_create(self, serializer):
        """Log CREATE actions."""
        instance = serializer.save()

        log_model_change(
            user=self.request.user,
            action_type="CREATE",
            instance=instance,
            request=self.request,
        )

        return instance

    def perform_update(self, serializer):
        """Log UPDATE actions with change tracking."""
        instance = serializer.instance

        # Capture old values
        old_values = {
            field: getattr(instance, field)
            for field in serializer.validated_data.keys()
            if hasattr(instance, field)
        }

        # Save changes
        instance = serializer.save()

        # Log with changes
        log_model_change(
            user=self.request.user,
            action_type="UPDATE",
            instance=instance,
            old_values=old_values,
            request=self.request,
        )

        return instance

    def perform_destroy(self, instance):
        """Log DELETE actions."""
        # Log BEFORE deletion
        log_model_change(
            user=self.request.user,
            action_type="DELETE",
            instance=instance,
            request=self.request,
        )

        instance.delete()
