# apps/reports/apis.py
from __future__ import annotations

from datetime import datetime

from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.services import (
    generate_spending_report,
    export_household_snapshot,
    ReportAccessError,
)


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    dt = parse_datetime(value)
    if not dt:
        raise ValueError(f"{field_name} must be an ISO-8601 datetime string.")
    return dt


class SpendingReportApi(APIView):
    """
    GET /api/v1/reports/spending/?from_date=...&to_date=...[&category_id=...]

    Requires:
      - Authorization: Bearer <token>
      - X-Household-ID header (or household_id query)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        raw_from = request.query_params.get("from_date")
        raw_to = request.query_params.get("to_date")
        raw_category = request.query_params.get("category_id")

        if not raw_from or not raw_to:
            return Response(
                {"detail": "from_date and to_date query params are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from_date = _parse_iso_datetime(raw_from, "from_date")
            to_date = _parse_iso_datetime(raw_to, "to_date")
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        household_id = request.headers.get(
            "X-Household-ID"
        ) or request.query_params.get("household_id")
        if not household_id:
            return Response(
                {
                    "detail": "X-Household-ID header or household_id query param is required."
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

        category_id = None
        if raw_category:
            try:
                category_id = int(raw_category)
            except ValueError:
                return Response(
                    {"detail": "category_id must be an integer."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            report = generate_spending_report(
                user=request.user,
                household_id=household_id_int,
                from_date=from_date,
                to_date=to_date,
                category_id=category_id,
            )
        except ReportAccessError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(report, status=status.HTTP_200_OK)


class HouseholdExportApi(APIView):
    """
    GET /api/v1/reports/household-export/

    Simple JSON export of accounts, budgets, goals, categories.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        household_id = request.headers.get(
            "X-Household-ID"
        ) or request.query_params.get("household_id")
        if not household_id:
            return Response(
                {
                    "detail": "X-Household-ID header or household_id query param is required."
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
            data = export_household_snapshot(
                user=request.user,
                household_id=household_id_int,
            )
        except ReportAccessError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        return Response(data, status=status.HTTP_200_OK)
