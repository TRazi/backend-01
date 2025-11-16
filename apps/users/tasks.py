"""
User-related Celery Tasks

Django Best Practice: Use @shared_task for reusability, implement retry logic
with exponential backoff, and use render_to_string for email templates.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task(bind=True, max_retries=3)
def send_verification_email(self, user_id: int, verification_token: str):
    """
    Send email verification link to user.

    Django Best Practice: Use bind=True for retry with self.retry(),
    implement exponential backoff for resilience.

    Args:
        user_id: User ID
        verification_token: Verification token (UUID string)

    Returns:
        str: Success message with user email
    """
    from users.models import User

    try:
        user = User.objects.get(id=user_id)

        # Build verification URL
        verification_url = (
            f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
        )

        # Render email template with context
        context = {
            "user": user,
            "verification_url": verification_url,
        }
        html_message = render_to_string("emails/verify_email.html", context)
        plain_message = strip_tags(html_message)

        # Send email
        send_mail(
            subject="Verify your KinWise account",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        return f"Verification email sent to {user.email}"

    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as exc:
        # Retry with exponential backoff: 60s, 120s, 240s
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_otp_email(self, user_id: int, otp_code: str):
    """
    Send OTP code to user for passwordless login.

    Args:
        user_id: User ID
        otp_code: 6-digit OTP code

    Returns:
        str: Success message with user email
    """
    from users.models import User

    try:
        user = User.objects.get(id=user_id)

        context = {
            "user": user,
            "otp_code": otp_code,
        }
        html_message = render_to_string("emails/login_otp.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Your KinWise login code",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

        return f"OTP email sent to {user.email}"

    except User.DoesNotExist:
        return f"User {user_id} not found"
    except Exception as exc:
        # Retry with shorter backoff for OTP (time-sensitive)
        raise self.retry(exc=exc, countdown=30 * (2**self.request.retries))


@shared_task
def send_welcome_email(user_id: int):
    """
    Send welcome email to new user after email verification.

    Args:
        user_id: User ID

    Returns:
        str: Success message with user email
    """
    from users.models import User

    try:
        user = User.objects.get(id=user_id)

        context = {"user": user}
        html_message = render_to_string("emails/welcome.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Welcome to KinWise!",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
        )

        return f"Welcome email sent to {user.email}"

    except User.DoesNotExist:
        return f"User {user_id} not found"


@shared_task(bind=True, max_retries=3)
def send_lockout_notification(
    self,
    user_email: str,
    ip_address: str,
    lockout_duration_minutes: int,
    unlock_token: str = None,
):
    """
    Send account lockout notification email to user.

    Includes self-service unlock link for user convenience and security.

    Args:
        user_email: User's email address
        ip_address: IP address that triggered the lockout
        lockout_duration_minutes: Duration of lockout in minutes
        unlock_token: Optional unlock token for self-service unlock

    Returns:
        str: Success message with user email
    """
    try:
        # Build unlock URL if token provided
        unlock_url = None
        if unlock_token:
            unlock_url = f"{settings.FRONTEND_URL}/unlock-account?token={unlock_token}"

        context = {
            "user_email": user_email,
            "ip_address": ip_address,
            "lockout_duration_minutes": lockout_duration_minutes,
            "unlock_url": unlock_url,
        }
        html_message = render_to_string("emails/account_lockout.html", context)
        plain_message = strip_tags(html_message)

        send_mail(
            subject="Security Alert: Account Temporarily Locked - KinWise",
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            html_message=html_message,
            fail_silently=False,
        )

        return f"Lockout notification sent to {user_email}"

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))
