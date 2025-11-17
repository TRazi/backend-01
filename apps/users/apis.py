# apps/users/apis.py
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from django.utils import timezone

from django.contrib.auth import get_user_model

# If you have audit logging, uncomment this:
from apps.audit.services import log_event

User = get_user_model()


class UserDataExportView(APIView):
    """
    Export all user-related data.
    Privacy Act 2020 — Right to Access (IPP 6)
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        data = {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "email_verified": user.email_verified,
            "locale": user.locale,
            "role": user.role,
            "household_id": user.household_id,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

        # Add optional audit logging
        # log_event(user, "USER_DATA_EXPORTED")

        return Response(data, status=status.HTTP_200_OK)


class CorrectionRequestView(APIView):
    """
    Users can request correction of their data.
    Privacy Act 2020 — Right to Correction (IPP 7)
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        request_data = request.data

        # Persist the request to your audit log or CRM workflow
        # log_event(user, "CORRECTION_REQUEST_SUBMITTED", extra=request_data)

        return Response(
            {
                "message": "Your correction request has been received.",
                "submitted_data": request_data,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class UserDeletionRequestView(APIView):
    """
    Users can request account deletion.
    Privacy Act 2020 — Right to Erasure (IPP 9)
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user

        # Mark account as pending deletion (soft workflow)
        user.is_active = False
        user.save(update_fields=["is_active", "updated_at"])

        # log_event(user, "USER_DELETION_REQUESTED")

        return Response(
            {"message": "Your deletion request has been submitted."},
            status=status.HTTP_202_ACCEPTED,
        )
