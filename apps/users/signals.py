import logging
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver
from axes.signals import user_locked_out

audit_logger = logging.getLogger("kinwise.audit")


def _get_ip(request):
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


def _get_ua(request):
    if not request:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    """Log successful login (JSON logs + database audit)."""
    audit_logger.info(
        "user_logged_in",
        extra={
            "event": "user_logged_in",
            "user_id": user.pk,
            "user_email": getattr(user, "email", None),
            "ip_address": _get_ip(request),
            "user_agent": _get_ua(request),
            "path": getattr(request, "path", None),
        },
    )

    # Create database audit record
    from audit.models import AuditLog

    AuditLog.objects.create(
        user=user,
        action_type="LOGIN",
        action_description=f"User {user.email} logged in successfully",
        ip_address=_get_ip(request),
        user_agent=_get_ua(request),
        request_path=getattr(request, "path", None),
        request_method="POST",
        success=True,
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    """Log user logout (JSON logs + database audit)."""
    audit_logger.info(
        "user_logged_out",
        extra={
            "event": "user_logged_out",
            "user_id": getattr(user, "pk", None),
            "user_email": getattr(user, "email", None) if user else None,
            "ip_address": _get_ip(request),
            "user_agent": _get_ua(request),
            "path": getattr(request, "path", None) if request else None,
        },
    )

    # Create database audit record
    if user:
        from audit.models import AuditLog

        AuditLog.objects.create(
            user=user,
            action_type="LOGOUT",
            action_description=f"User {user.email} logged out",
            ip_address=_get_ip(request),
            user_agent=_get_ua(request),
            request_path=getattr(request, "path", None) if request else None,
            request_method="POST",
            success=True,
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    """Log failed login attempt (JSON logs + database audit)."""
    username = credentials.get("username", "unknown")
    ip = _get_ip(request)

    audit_logger.info(
        "user_login_failed",
        extra={
            "event": "user_login_failed",
            "user_email": username,
            "ip_address": ip,
            "user_agent": _get_ua(request),
            "path": getattr(request, "path", None) if request else None,
        },
    )

    # Create database audit record
    from audit.models import AuditLog, FailedLoginAttempt

    AuditLog.objects.create(
        user=None,  # No user for failed login
        action_type="LOGIN_FAILED",
        action_description=f"Failed login attempt for {username}",
        ip_address=ip,
        user_agent=_get_ua(request),
        request_path=getattr(request, "path", None) if request else None,
        request_method="POST",
        success=False,
        metadata={"username": username},
    )

    # Track failed login attempt
    FailedLoginAttempt.objects.create(
        username=username,
        ip_address=ip,
        user_agent=_get_ua(request),
        request_path=getattr(request, "path", None) if request else None,
    )


@receiver(user_locked_out)
def handle_user_locked_out(sender, request, username, **kwargs):
    """
    Handle Axes lockout event by sending notification email with unlock token.

    This is triggered when a user exceeds the maximum login attempts (5 failures).
    """
    from apps.users.models import AccountUnlockToken
    from apps.users.tasks import send_lockout_notification
    from django.conf import settings

    ip_address = _get_ip(request)

    audit_logger.warning(
        "user_locked_out",
        extra={
            "event": "user_locked_out",
            "username": username,
            "ip_address": ip_address,
            "user_agent": _get_ua(request),
            "path": getattr(request, "path", None) if request else None,
        },
    )

    # Create database audit record
    from audit.models import AuditLog

    AuditLog.objects.create(
        user=None,
        action_type="ACCOUNT_LOCKED",
        action_description=f"Account locked due to too many failed login attempts: {username}",
        ip_address=ip_address,
        user_agent=_get_ua(request),
        request_path=getattr(request, "path", None) if request else None,
        request_method="POST",
        success=False,
        metadata={
            "username": username,
            "reason": "Too many failed login attempts",
        },
    )

    # Create unlock token for self-service unlock
    unlock_token = AccountUnlockToken.objects.create(
        email=username,  # Axes uses username field which is email in our case
        ip_address=ip_address,
    )

    # Send lockout notification email asynchronously
    # Get lockout duration from settings (default 60 minutes)
    lockout_duration = getattr(settings, "AXES_COOLOFF_TIME", 1)  # In hours
    if isinstance(lockout_duration, int):
        lockout_duration_minutes = lockout_duration * 60
    else:
        lockout_duration_minutes = 60

    send_lockout_notification.delay(
        user_email=username,
        ip_address=ip_address,
        lockout_duration_minutes=lockout_duration_minutes,
        unlock_token=str(unlock_token.token),
    )

    audit_logger.info(
        "lockout_notification_queued",
        extra={
            "event": "lockout_notification_queued",
            "email": username,
            "unlock_token_id": unlock_token.id,
        },
    )
