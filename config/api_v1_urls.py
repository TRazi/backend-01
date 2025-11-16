from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from config.views.session import SessionPingView
from users.views_auth import MFATokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from users.views import UserRegistrationView
from users.views_otp import EmailOTPViewSet
from users.views_verification import VerifyEmailView, ResendVerificationView

# Router for ViewSets
router = DefaultRouter()
router.register(r"auth/otp", EmailOTPViewSet, basename="email-otp")

urlpatterns = [
    # JWT Authentication
    path("auth/token/", MFATokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/", include("users.auth_urls")),
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
    path("", include("accounts.api_urls")),
    path("", include("alerts.api_urls")),
    path("", include("audit.api_urls")),
    path("", include("bills.api_urls")),
    path("", include("budgets.api_urls")),
    path("", include("categories.api_urls")),
    path("", include("goals.api_urls")),
    path("households/", include("households.api_urls")),
    path("", include("lessons.api_urls")),
    path("", include("organisations.api_urls")),
    path("", include("rewards.api_urls")),
    path("", include("transactions.api_urls")),
    path("", include("users.api_urls")),
    path("", include("reports.api_urls")),
    path("privacy/", include("privacy.api_urls")),
]
