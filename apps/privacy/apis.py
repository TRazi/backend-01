# apps/privacy/apis.py
from __future__ import annotations

from django.http import Http404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.privacy.services import (
    export_user_data,
    request_data_deletion,
    get_data_deletion_status,
    HouseholdAccessError,
)


class DataExportApi(APIView):
    """
    GDPR / NZ Privacy Act data export endpoint.

    GET /api/v1/privacy/data-export/?household_id=1
    Requires:
      - Authenticated user
      - Membership in the household
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        household_id = request.query_params.get("household_id") or request.headers.get(
            "X-Household-ID"
        )
        if not household_id:
            return Response(
                {
                    "detail": "household_id query param or X-Household-ID header is required."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            household_id_int = int(household_id)
        except ValueError:
            return Response(
                {"detail": "household_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = export_user_data(user=request.user, household_id=household_id_int)
        except HouseholdAccessError as exc:
            # We deliberately blur 404/403 into 404-ish semantics to avoid
            # leaking the existence of households the user can't access.
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(data, status=status.HTTP_200_OK)


class DataDeletionRequestApi(APIView):
    """
    POST to request deletion, GET to check status.
    These are user-centric, not household-centric.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        result = request_data_deletion(user=request.user)
        return Response(result, status=status.HTTP_202_ACCEPTED)

    def get(self, request, *args, **kwargs):
        result = get_data_deletion_status(user=request.user)
        return Response(result, status=status.HTTP_200_OK)


class PrivacyInfoApi(APIView):
    """
    Returns static / semi-static privacy information.
    In v1 this often backs 'Privacy Policy' and 'How we handle your data' pages.
    """

    authentication_classes: list = []  # public
    permission_classes: list = []  # public

    def get(self, request, *args, **kwargs):
        # You can later wire this to a CMS table if needed.
        return Response(
            {
                "product": "Kinwise",
                "jurisdiction": ["NZ Privacy Act 2020", "GDPR (where applicable)"],
                "data_subject_rights": [
                    "Right to access",
                    "Right to rectification",
                    "Right to erasure",
                    "Right to restriction of processing",
                    "Right to data portability",
                ],
                "contact_email": "privacy@kinwise.co.nz",
                "last_updated": "2025-01-01",
            }
        )
