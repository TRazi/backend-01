"""
Email Verification Views

Django Best Practice: Use APIView for simple endpoints,
proper error handling, and security best practices.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.core.exceptions import ValidationError

from users.models import User, EmailVerification
from audit.services import log_action


class VerifyEmailView(APIView):
    """
    Verify user email with token from email link.
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        """
        Verify email token.

        Query params: ?token=<uuid>
        Response: {"message": "...", "user": {...}}
        """
        token = request.query_params.get("token")

        if not token:
            return Response(
                {"error": "Verification token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            verification = EmailVerification.objects.get(token=token)

            if verification.is_verified():
                return Response(
                    {"message": "Email already verified"}, status=status.HTTP_200_OK
                )

            if verification.is_expired():
                return Response(
                    {"error": "Verification token has expired"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify email (uses @transaction.atomic)
            if verification.verify():
                # Log verification
                log_action(
                    user=verification.user,
                    action_type="EMAIL_VERIFIED",
                    action_description=f"Email verified: {verification.user.email}",
                    request=request,
                )

                return Response(
                    {
                        "message": "Email verified successfully",
                        "user": {
                            "email": verification.user.email,
                            "is_active": verification.user.is_active,
                        },
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {"error": "Verification failed"}, status=status.HTTP_400_BAD_REQUEST
            )

        except (EmailVerification.DoesNotExist, ValidationError):
            return Response(
                {"error": "Invalid verification token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ResendVerificationView(APIView):
    """
    Resend verification email to user.
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """
        Resend verification email.

        Request: {"email": "user@example.com"}
        Response: {"message": "..."}
        """
        from users.tasks import send_verification_email

        email = request.data.get("email", "").lower().strip()

        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(email=email)

            if user.is_active and user.email_verified:
                return Response(
                    {"message": "Email already verified"}, status=status.HTTP_200_OK
                )

            # Get or create verification
            verification, created = EmailVerification.objects.get_or_create(user=user)

            if not created and not verification.is_expired():
                # Reuse existing token
                pass
            elif not created and verification.is_expired():
                # Delete expired token and create new one
                verification.delete()
                verification = EmailVerification.objects.create(user=user)
            # else: created is True, use the new verification

            # Send verification email (async)
            send_verification_email.delay(user.id, str(verification.token))

            return Response(
                {"message": "Verification email sent"}, status=status.HTTP_200_OK
            )

        except User.DoesNotExist:
            # Security: Don't reveal if email exists
            return Response(
                {"message": "If the email exists, a verification email has been sent."},
                status=status.HTTP_200_OK,
            )
