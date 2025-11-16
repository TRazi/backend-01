import logging
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

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
