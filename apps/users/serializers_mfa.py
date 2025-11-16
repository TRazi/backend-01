# apps/users/serializers_mfa.py
from rest_framework import serializers

from .services.mfa import (
    generate_provisioning_uri,
    verify_totp_code,
    generate_backup_codes,
    enable_mfa,
    verify_backup_code,
)


class MFABeginSetupSerializer(serializers.Serializer):
    provisioning_uri = serializers.CharField(read_only=True)


class MFAConfirmSetupSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        user = self.context["request"].user
        code = attrs["code"]

        if not verify_totp_code(user, code):
            raise serializers.ValidationError({"code": "Invalid TOTP code"})
        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        enable_mfa(user)
        # Generate backup codes after enabling
        raw_codes = generate_backup_codes(user)
        return {"backup_codes": raw_codes}


class MFABackupCodeVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=32)

    def validate(self, attrs):
        user = self.context["request"].user
        code = attrs["code"]

        if not verify_backup_code(user, code):
            raise serializers.ValidationError({"code": "Invalid backup code"})
        return attrs
