"""
Account unlock views for self-service recovery from Axes lockouts.
"""

import logging
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle
from django.utils import timezone

from users.models import AccountUnlockToken

logger = logging.getLogger(__name__)


class UnlockAccountThrottle(AnonRateThrottle):
    """Custom throttle for unlock endpoint - 3 attempts per hour."""

    rate = "3/hour"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([UnlockAccountThrottle])
def unlock_account_view(request):
    """
    Unlock account using a one-time unlock token.

    Validates the token and clears Axes lockout for the associated email.

    Request body:
        {
            "token": "uuid-string"
        }

    Returns:
        200: Account successfully unlocked
        400: Invalid or expired token
        429: Too many unlock attempts
    """
    token_str = request.data.get("token")

    if not token_str:
        return Response(
            {
                "error_code": "MISSING_TOKEN",
                "message": "Unlock token is required",
                "user_message": "Please provide a valid unlock link.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        # Fetch the unlock token
        unlock_token = AccountUnlockToken.objects.get(token=token_str)

        # Check if token is valid
        if not unlock_token.is_valid():
            logger.warning(
                f"Invalid unlock token attempt: {token_str} "
                f"(email: {unlock_token.email}, "
                f"expired: {unlock_token.expires_at < timezone.now()}, "
                f"used: {unlock_token.used_at is not None})"
            )
            return Response(
                {
                    "error_code": "INVALID_TOKEN",
                    "message": "Token is expired or already used",
                    "user_message": "This unlock link has expired or has already been used.",
                    "hint": "Try logging in again. If locked out, request a new unlock link.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset Axes lockout for this email/username
        # Clear all access attempts for this username
        from axes.models import AccessAttempt

        AccessAttempt.objects.filter(username=unlock_token.email).delete()

        # Mark token as used
        unlock_token.mark_as_used()

        logger.info(
            f"Account unlocked successfully: {unlock_token.email} "
            f"(token: {token_str}, IP: {request.META.get('REMOTE_ADDR')})"
        )

        # Create audit log
        from audit.models import AuditLog

        AuditLog.objects.create(
            user=None,
            action_type="ACCOUNT_UNLOCKED",
            action_description=f"Account unlocked via self-service token: {unlock_token.email}",
            ip_address=request.META.get("REMOTE_ADDR"),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            request_path=request.path,
            request_method="POST",
            success=True,
            metadata={
                "email": unlock_token.email,
                "unlock_token_id": unlock_token.id,
            },
        )

        return Response(
            {
                "message": "Account unlocked successfully",
                "user_message": "Your account has been unlocked! You can now log in.",
                "email": unlock_token.email,
            },
            status=status.HTTP_200_OK,
        )

    except AccountUnlockToken.DoesNotExist:
        logger.warning(f"Unknown unlock token attempt: {token_str}")
        return Response(
            {
                "error_code": "INVALID_TOKEN",
                "message": "Token not found",
                "user_message": "This unlock link is not valid.",
                "hint": "Make sure you copied the full URL from your email.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        logger.error(f"Error unlocking account: {str(e)}", exc_info=True)
        return Response(
            {
                "error_code": "UNLOCK_FAILED",
                "message": "Failed to unlock account",
                "user_message": "Something went wrong. Please try again or contact support.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
