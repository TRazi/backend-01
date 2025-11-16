import secrets
from typing import List

import pyotp
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.conf import settings

ISSUER_NAME = getattr(settings, "MFA_ISSUER_NAME", "KinWise")


# -------------------------
# Lazy model accessors
# -------------------------


def get_user_model():
    from django.contrib.auth import get_user_model

    return get_user_model()


def get_mfa_device_model():
    from users.models import UserMFADevice

    return UserMFADevice


# -------------------------
# MFA Core Functions
# -------------------------


def get_or_create_mfa_device(user):
    mfa_device_model = get_mfa_device_model()

    device, _ = mfa_device_model.objects.get_or_create(
        user=user,
        defaults={
            "secret_key": pyotp.random_base32(),
            "is_enabled": False,
            "backup_codes": [],
        },
    )
    return device


def generate_provisioning_uri(user) -> str:
    device = get_or_create_mfa_device(user)
    totp = pyotp.TOTP(device.secret_key)
    return totp.provisioning_uri(name=user.email, issuer_name=ISSUER_NAME)


def verify_totp_code(user, code: str, valid_window: int = 1) -> bool:
    mfa_device_model = get_mfa_device_model()

    try:
        device = user.mfa_device
    except mfa_device_model.DoesNotExist:
        return False

    totp = pyotp.TOTP(device.secret_key)
    is_valid = totp.verify(code, valid_window=valid_window)

    if is_valid:
        device.last_used_at = timezone.now()
        device.save(update_fields=["last_used_at"])

    return is_valid


def _generate_backup_code() -> str:
    return secrets.token_urlsafe(8)


def generate_backup_codes(user, count: int = 10) -> List[str]:
    device = get_or_create_mfa_device(user)

    raw_codes = [_generate_backup_code() for _ in range(count)]
    hashed = [make_password(code) for code in raw_codes]

    device.backup_codes = hashed
    device.save(update_fields=["backup_codes"])

    return raw_codes


def verify_backup_code(user, code: str) -> bool:
    mfa_device_model = get_mfa_device_model()

    try:
        device = user.mfa_device
    except mfa_device_model.DoesNotExist:
        return False

    for idx, hashed in enumerate(device.backup_codes):
        if check_password(code, hashed):
            # consume the backup code
            device.backup_codes.pop(idx)
            device.last_used_at = timezone.now()
            device.save(update_fields=["backup_codes", "last_used_at"])
            return True

    return False


def enable_mfa(user):
    device = get_or_create_mfa_device(user)
    device.is_enabled = True
    device.save(update_fields=["is_enabled"])


def disable_mfa(user):
    mfa_device_model = get_mfa_device_model()

    try:
        device = user.mfa_device
    except mfa_device_model.DoesNotExist:
        return

    device.is_enabled = False
    device.backup_codes = []
    device.save(update_fields=["is_enabled", "backup_codes"])
