from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from config.views.session import SessionPingView
from apps.users.views_auth import MFATokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from apps.users.views import UserRegistrationView
from apps.users.views_otp import EmailOTPViewSet
from apps.users.views_verification import VerifyEmailView, ResendVerificationView

# Router for ViewSets
router = DefaultRouter()
router.register(r"auth/otp", EmailOTPViewSet, basename="email-otp")

urlpatterns = [
    # JWT Authentication
    path("auth/token/", MFATokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/", include("apps.users.auth_urls")),
    # User Registration & Email Verification
    path("auth/register/", UserRegistrationView.as_view(), name="user-registration"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path(
        "auth/resend-verification/",
        ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    # Session management
    path("session/ping/", SessionPingView.as_view(), name="session-ping"),
    # Router URLs (includes OTP endpoints)
    path("", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Domain apps
    path("", include("apps.accounts.api_urls")),
    path("", include("apps.alerts.api_urls")),
    path("", include("apps.audit.api_urls")),
    path("", include("apps.bills.api_urls")),
    path("", include("apps.budgets.api_urls")),
    path("", include("apps.categories.api_urls")),
    path("", include("apps.goals.api_urls")),
    path("households/", include("apps.households.api_urls")),
    path("", include("apps.lessons.api_urls")),
    path("", include("apps.organisations.api_urls")),
    path("", include("apps.rewards.api_urls")),
    path("", include("apps.transactions.api_urls")),
    path("", include("apps.users.api_urls")),
    path("", include("apps.reports.api_urls")),
    path("privacy/", include("apps.privacy.api_urls")),
]
