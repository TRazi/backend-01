from django.urls import path
from .apis import DataExportApi, DataDeletionRequestApi, PrivacyInfoApi

app_name = "privacy"

urlpatterns = [
    path("data-export/", DataExportApi.as_view(), name="data-export"),
    path("delete-request/", DataDeletionRequestApi.as_view(), name="delete-request"),
    path("info/", PrivacyInfoApi.as_view(), name="info"),
]
