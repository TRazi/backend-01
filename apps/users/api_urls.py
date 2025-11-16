# apps/users/api_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet
from .apis import (
    UserDataExportView,
    CorrectionRequestView,
    UserDeletionRequestView,
)

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("users/me/data-export/", UserDataExportView.as_view()),
    path("users/me/correction-request/", CorrectionRequestView.as_view()),
    path("users/me/delete-request/", UserDeletionRequestView.as_view()),
]
