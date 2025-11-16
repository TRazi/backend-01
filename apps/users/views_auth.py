# apps/users/views_auth.py
import logging
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from .serializers_auth import MFATokenObtainPairSerializer

logger = logging.getLogger(__name__)


class MFATokenObtainPairView(TokenObtainPairView):
    """
    Enhanced JWT token authentication with detailed logging and error handling.

    Improvements:
    - Detailed logging for debugging login issues
    - User-friendly error messages
    - IP address tracking for security
    - Lockout detection and clear messaging
    """

    serializer_class = MFATokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # Get client IP for logging
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(",")[0]
        else:
            ip_address = request.META.get("REMOTE_ADDR", "unknown")

        email_or_username = request.data.get("email") or request.data.get("username")

        logger.info(
            f"Login attempt: user={email_or_username}, ip={ip_address}, "
            f"timestamp={timezone.now().isoformat()}"
        )

        try:
            response = super().post(request, *args, **kwargs)

            # Successful login
            logger.info(f"Login successful: user={email_or_username}, ip={ip_address}")

            return response

        except Exception as e:
            # Log the error with details
            logger.warning(
                f"Login failed: user={email_or_username}, ip={ip_address}, "
                f"error={str(e)}, error_type={type(e).__name__}"
            )

            # Check if this is an Axes lockout
            from axes.helpers import get_failure_limit, get_cool_off_iso8601
            from axes.models import AccessAttempt

            # Check for lockout
            try:
                attempts = (
                    AccessAttempt.objects.filter(username=email_or_username)
                    .order_by("-attempt_time")
                    .first()
                )

                if attempts and attempts.failures_since_start >= get_failure_limit():
                    lockout_duration = get_cool_off_iso8601()
                    logger.error(
                        f"Account locked out: user={email_or_username}, ip={ip_address}, "
                        f"attempts={attempts.failures_since_start}"
                    )
                    return Response(
                        {
                            "error": "account_locked",
                            "error_code": "ACCOUNT_LOCKED",
                            "message": "Your account has been temporarily locked due to multiple failed login attempts.",
                            "user_message": "Too many failed attempts. Please try again in 1 hour or contact support.",
                            "lockout_duration": "1 hour",
                            "support_email": "support@kinwise.co.nz",
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            except Exception as lockout_check_error:
                logger.error(f"Error checking lockout status: {lockout_check_error}")

            # Enhanced error response for validation errors
            if hasattr(e, "detail"):
                error_detail = str(e.detail) if hasattr(e.detail, "__str__") else str(e)

                # Check for common error patterns
                if "MFA" in error_detail or "otp" in error_detail.lower():
                    return Response(
                        {
                            "error": "mfa_required",
                            "error_code": "MFA_REQUIRED",
                            "message": "Multi-factor authentication code required.",
                            "user_message": "Please enter your 6-digit authentication code.",
                            "dev_details": error_detail,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if (
                    "credentials" in error_detail.lower()
                    or "password" in error_detail.lower()
                ):
                    return Response(
                        {
                            "error": "invalid_credentials",
                            "error_code": "INVALID_CREDENTIALS",
                            "message": "The email/username or password you entered is incorrect.",
                            "user_message": "Invalid credentials. Please check your email and password and try again.",
                            "hint": "Make sure Caps Lock is off and try again.",
                        },
                        status=status.HTTP_401_UNAUTHORIZED,
                    )

            # Generic error response with helpful message
            return Response(
                {
                    "error": "authentication_failed",
                    "error_code": "AUTH_FAILED",
                    "message": "Authentication failed. Please check your credentials and try again.",
                    "user_message": "We couldn't log you in. Please verify your email and password.",
                    "dev_details": (
                        str(e) if logger.isEnabledFor(logging.DEBUG) else None
                    ),
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )
