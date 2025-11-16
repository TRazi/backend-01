# apps/users/serializers_auth.py
import logging
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

from .services.mfa import verify_totp_code, verify_backup_code

logger = logging.getLogger(__name__)


class MFATokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Enhanced JWT serializer with MFA support and detailed error messages.
    """

    otp = serializers.CharField(
        required=False, allow_blank=True, help_text="6-digit MFA code"
    )
    backup_code = serializers.CharField(
        required=False, allow_blank=True, help_text="8-character backup code"
    )

    def validate(self, attrs):
        try:
            data = super().validate(attrs)
        except serializers.ValidationError as e:
            # Log authentication failure
            email = attrs.get("email")
            logger.warning(f"Initial auth failed for {email}: {str(e)}")

            # Enhance error message
            raise serializers.ValidationError(
                {
                    "error": "invalid_credentials",
                    "message": "Unable to authenticate with provided credentials.",
                    "hint": "Please check your email and password.",
                }
            )

        user = self.user

        device = getattr(user, "mfa_device", None)
        if device and device.is_enabled:
            otp = attrs.get("otp")
            backup_code = attrs.get("backup_code")

            if not otp and not backup_code:
                logger.info(f"MFA required for user {user.email}")
                raise serializers.ValidationError(
                    {
                        "error": "mfa_required",
                        "message": "Multi-factor authentication is enabled for this account.",
                        "hint": "Please provide your 6-digit authentication code or a backup code.",
                        "mfa_enabled": True,
                    }
                )

            if otp:
                if verify_totp_code(user, otp):
                    logger.info(f"MFA successful for user {user.email} (TOTP)")
                    return data
                else:
                    logger.warning(f"Invalid TOTP code for user {user.email}")

            if backup_code:
                if verify_backup_code(user, backup_code):
                    logger.info(f"MFA successful for user {user.email} (backup code)")
                    return data
                else:
                    logger.warning(f"Invalid backup code for user {user.email}")

            raise serializers.ValidationError(
                {
                    "error": "invalid_mfa",
                    "message": "The authentication code you entered is invalid.",
                    "hint": "Make sure you're using the latest code from your authenticator app.",
                }
            )

        # No MFA configured; successful login
        logger.info(f"Login successful for user {user.email} (no MFA)")
        return data
