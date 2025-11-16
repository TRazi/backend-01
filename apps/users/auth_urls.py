# apps/users/auth_urls.py
from django.urls import path

from .views_mfa import (
    MFABeginSetupView,
    MFAConfirmSetupView,
    MFABackupCodeVerifyView,
)

urlpatterns = [
    path("mfa/setup/begin/", MFABeginSetupView.as_view(), name="mfa-setup-begin"),
    path("mfa/setup/confirm/", MFAConfirmSetupView.as_view(), name="mfa-setup-confirm"),
    path(
        "mfa/backup/verify/",
        MFABackupCodeVerifyView.as_view(),
        name="mfa-backup-verify",
    ),
]
