# apps/users/api_urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import UserViewSet
from .apis import (
    UserDataExportView,
    CorrectionRequestView,
    UserDeletionRequestView,
)
from .views_unlock import unlock_account_view

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    path("", include(router.urls)),
    path("users/me/data-export/", UserDataExportView.as_view()),
    path("users/me/correction-request/", CorrectionRequestView.as_view()),
    path("users/me/delete-request/", UserDeletionRequestView.as_view()),
    path("auth/unlock-account/", unlock_account_view, name="unlock-account"),
]
