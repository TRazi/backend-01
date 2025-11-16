# apps/reports/api_urls.py
from django.urls import path

from .apis import SpendingReportApi, HouseholdExportApi

app_name = "reports"

urlpatterns = [
    path("reports/spending/", SpendingReportApi.as_view(), name="spending-report"),
    path("backups/export/", HouseholdExportApi.as_view(), name="household-export"),
]
