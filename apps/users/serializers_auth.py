# apps/users/serializers_auth.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers

from .services.mfa import verify_totp_code, verify_backup_code


class MFATokenObtainPairSerializer(TokenObtainPairSerializer):
    otp = serializers.CharField(required=False, allow_blank=True)
    backup_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        device = getattr(user, "mfa_device", None)
        if device and device.is_enabled:
            otp = attrs.get("otp")
            backup_code = attrs.get("backup_code")

            if not otp and not backup_code:
                raise serializers.ValidationError(
                    {"detail": "MFA code required for this account."}
                )

            if otp and verify_totp_code(user, otp):
                return data

            if backup_code and verify_backup_code(user, backup_code):
                return data

            raise serializers.ValidationError({"detail": "Invalid MFA credentials."})

        # No MFA configured; you can tighten this later for high-privileged roles
        return data
