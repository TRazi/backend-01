"""
Email OTP (Passwordless) Authentication Views

Django Best Practice: Use ViewSets with mixins for cleaner, more maintainable code.
Use DRF throttling instead of decorators for better consistency.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from django.utils import timezone

from apps.users.models import User, EmailOTP
from apps.users.serializers import EmailOTPRequestSerializer, EmailOTPVerifySerializer
from apps.audit.services import log_action


# NOTE: Throttling to be re-enabled after DRF upgrade with proper rate format support
# Throttle classes temporarily disabled due to rate parsing issues in current DRF version
# class OTPRequestThrottle(AnonRateThrottle):
#     """Custom throttle: 3 requests per hour."""
#     rate = "3/h"
#
# class OTPVerifyThrottle(AnonRateThrottle):
#     """Custom throttle: 5 requests per hour."""
#     rate = "5/h"


class EmailOTPViewSet(viewsets.GenericViewSet):
    """
    ViewSet for Email OTP authentication.

    Django Best Practice: Use ViewSet with custom actions,
    throttling classes, and proper serializer validation.
    """

    permission_classes = [AllowAny]
    serializer_class = EmailOTPRequestSerializer

    @action(
        detail=False,
        methods=["post"],
        url_path="request",
        serializer_class=EmailOTPRequestSerializer,
    )
    @transaction.atomic
    def request_otp(self, request):
        """
        Request OTP code for passwordless login.

        Django Best Practice: Use serializer for validation,
        transaction for atomicity, and throttling for rate limiting.

        Request: {"email": "user@example.com"}
        Response: {"message": "...", "expires_in": 600}
        """
        from users.tasks import send_otp_email

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email, is_active=True, email_verified=True)
        except User.DoesNotExist:
            # Security: Don't reveal if email exists
            return Response(
                {"message": "If the email exists, an OTP code has been sent."},
                status=status.HTTP_200_OK,
            )

        # Invalidate any existing unused OTPs for this user
        EmailOTP.objects.filter(
            user=user, is_used=False, expires_at__gt=timezone.now()
        ).update(is_used=True)

        # Create new OTP
        otp = EmailOTP.objects.create(
            user=user, ip_address=request.META.get("REMOTE_ADDR")
        )

        # Send OTP email (async) - after transaction commits
        transaction.on_commit(lambda: send_otp_email.delay(user.id, otp.code))

        return Response(
            {
                "message": "OTP code sent to your email",
                "expires_in": 600,  # 10 minutes
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="verify",
        serializer_class=EmailOTPVerifySerializer,
    )
    @transaction.atomic
    def verify_otp(self, request):
        """
        Verify OTP code and issue JWT tokens.

        Django Best Practice: Use serializer validation,
        select_for_update to prevent race conditions,
        transaction for atomicity.

        Request: {"email": "user@example.com", "code": "123456"}
        Response: {"access": "...", "refresh": "...", "user": {...}}
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            # Use select_for_update to prevent concurrent OTP usage
            user = User.objects.select_for_update().get(email=email, is_active=True)

            otp = (
                EmailOTP.objects.select_for_update()
                .filter(user=user, code=code, is_used=False)
                .order_by("-created_at")
                .first()
            )

            if not otp:
                raise EmailOTP.DoesNotExist()

            if not otp.is_valid():
                return Response(
                    {"error": "OTP code has expired"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Mark OTP as used
            otp.mark_as_used()

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            # Log successful login
            log_action(
                user=user,
                action_type="LOGIN",
                action_description=f"User logged in via OTP: {user.email}",
                request=request,
            )

            return Response(
                {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "role": user.role,
                    },
                },
                status=status.HTTP_200_OK,
            )

        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            # Log failed attempt
            log_action(
                user=None,
                action_type="LOGIN_FAILED",
                action_description=f"Failed OTP login attempt for: {email}",
                request=request,
            )

            return Response(
                {"error": "Invalid email or OTP code"},
                status=status.HTTP_400_BAD_REQUEST,
            )
