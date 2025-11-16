# apps/users/models.py
import uuid
import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils import timezone
from django.core.cache import cache

from apps.common.models import BaseModel
from apps.users.managers import UserManager
from apps.users.enums import ROLE_CHOICES, LOCALE_CHOICES


class User(BaseModel, AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the unique identifier.
    Email is normalized to lowercase for case-insensitive matching.

    Features:
    - UUID for external API/public references (prevents ID enumeration)
    - Email uniqueness at database level
    - Automatic rate limiting on account creation
    - Enforced email verification for sensitive operations
    """

    # Phone validator for international format
    phone_regex = RegexValidator(
        regex=r"^\+?1?\d{9,15}$",
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.",
    )

    # Public UUID identifier (for external APIs, prevents ID enumeration)
    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Unique UUID for external API references",
    )

    username = models.CharField(
        max_length=150,
        unique=True,
        db_index=True,
        null=True,
        blank=True,
        help_text="Username for login (alternative to email)",
    )

    email = models.EmailField(unique=True, db_index=True)
    email_verified = models.BooleanField(default=False)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(validators=[phone_regex], max_length=17, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    locale = models.CharField(
        max_length=10,
        choices=LOCALE_CHOICES,
        default="en-nz",
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="observer")

    # Foreign key to household - optional
    household = models.ForeignKey(
        "households.Household",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
        indexes = [
            models.Index(fields=["email", "is_active"]),
            models.Index(fields=["username", "is_active"]),
            models.Index(fields=["uuid"]),
        ]

    def __str__(self):
        return self.email

    def clean(self):
        """Validate model fields."""
        super().clean()
        self.email = self.email.lower()

    def save(self, *args, **kwargs):
        """Normalize email to lowercase before saving."""
        self.email = self.email.lower()
        super().save(*args, **kwargs)

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.email

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email

    @classmethod
    def check_creation_rate_limit(
        cls, ip_address: str, max_accounts: int = 5, window_seconds: int = 3600
    ) -> bool:
        """
        Check if IP address has exceeded account creation rate limit.
        Prevents automated account creation attacks.

        Args:
            ip_address: IP address to check
            max_accounts: Maximum accounts allowed per window (default: 5)
            window_seconds: Time window in seconds (default: 3600 = 1 hour)

        Returns:
            bool: True if rate limit exceeded, False otherwise
        """
        cache_key = f"user_creation_rate_{ip_address}"
        current_count = cache.get(cache_key, 0)
        return current_count >= max_accounts

    @classmethod
    def increment_creation_rate_limit(
        cls, ip_address: str, window_seconds: int = 3600
    ) -> None:
        """
        Increment the account creation counter for an IP address.

        Args:
            ip_address: IP address to track
            window_seconds: Time window in seconds
        """
        cache_key = f"user_creation_rate_{ip_address}"
        current_count = cache.get(cache_key, 0)
        cache.set(cache_key, current_count + 1, window_seconds)

    def is_email_verified_for_action(self) -> bool:
        """
        Check if email is verified (required for sensitive operations).
        Can be used to gate access to sensitive features.

        Returns:
            bool: True if email is verified, False otherwise
        """
        return self.email_verified


class UserMFADevice(BaseModel):
    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="mfa_device",
    )
    # Base32 TOTP secret
    secret_key = models.CharField(max_length=64)
    # Whether MFA is active
    is_enabled = models.BooleanField(default=False)
    # Backup codes (hashed)
    backup_codes = models.JSONField(default=list, blank=True)
    # Last time an MFA code was used
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "MFA device"
        verbose_name_plural = "MFA devices"

    def __str__(self):
        return f"MFA device for {self.user.email}"


class EmailOTP(BaseModel):
    """
    One-Time Password for passwordless email login.
    OTP codes are valid for 10 minutes and can only be used once.

    Django Best Practice: Inherit from BaseModel for created_at/updated_at,
    use validators for code format, include help_text for documentation.
    """

    # Validator for 6-digit code
    code_validator = RegexValidator(
        regex=r"^\d{6}$",
        message="OTP code must be exactly 6 digits",
    )

    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="email_otps",
        verbose_name="User",
        help_text="User associated with this OTP",
    )
    code = models.CharField(
        max_length=6,
        validators=[code_validator],
        verbose_name="OTP Code",
        help_text="6-digit one-time password",
    )
    expires_at = models.DateTimeField(
        verbose_name="Expiration Time",
        help_text="When this OTP expires (10 minutes from creation)",
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name="Used",
        help_text="Whether this OTP has been used",
        db_index=True,
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP Address",
        help_text="IP address that requested this OTP",
    )

    class Meta:
        db_table = "email_otp"
        verbose_name = "Email OTP"
        verbose_name_plural = "Email OTPs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["code", "is_used"]),
            models.Index(fields=["expires_at", "is_used"]),
        ]
        permissions = [
            ("can_generate_otp", "Can generate OTP codes"),
            ("can_verify_otp", "Can verify OTP codes"),
        ]

    def save(self, *args, **kwargs):
        """Generate OTP code and set expiration on creation."""
        if not self.pk:
            # Generate secure 6-digit code
            self.code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
            # Set expiration (10 minutes)
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        """
        Check if OTP is still valid.

        Returns:
            bool: True if OTP is unused and not expired
        """
        return not self.is_used and timezone.now() < self.expires_at

    def mark_as_used(self):
        """Mark OTP as used (idempotent)."""
        if not self.is_used:
            self.is_used = True
            self.save(update_fields=["is_used", "updated_at"])

    def __str__(self):
        return f"OTP for {self.user.email} - {'Used' if self.is_used else 'Valid'}"


class EmailVerification(BaseModel):
    """
    Email verification token for new user registration.
    Tokens expire after 24 hours.

    Django Best Practice: Use BaseModel, add help_text, use @transaction.atomic
    for verify() method to ensure data consistency.
    """

    user = models.OneToOneField(
        "User",
        on_delete=models.CASCADE,
        related_name="email_verification",
        verbose_name="User",
        help_text="User to be verified",
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        verbose_name="Verification Token",
        help_text="Unique token sent to user email",
        db_index=True,
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Verified At",
        help_text="When email was verified",
    )

    class Meta:
        db_table = "email_verification"
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["token"]),
            models.Index(fields=["user", "verified_at"]),
        ]
        permissions = [
            ("can_verify_email", "Can verify user emails"),
            ("can_resend_verification", "Can resend verification emails"),
        ]

    def is_expired(self):
        """
        Check if verification token has expired (24 hours).

        Returns:
            bool: True if token is older than 24 hours
        """
        return timezone.now() > self.created_at + timedelta(hours=24)

    def is_verified(self):
        """
        Check if email has been verified.

        Returns:
            bool: True if verified_at is set
        """
        return self.verified_at is not None

    @transaction.atomic
    def verify(self):
        """
        Mark email as verified and activate user.
        Uses transaction to ensure atomicity.

        Django Best Practice: Use @transaction.atomic to ensure
        both verification and user activation succeed together.

        Returns:
            bool: True if verification succeeded, False otherwise
        """
        if not self.is_verified() and not self.is_expired():
            self.verified_at = timezone.now()
            self.save(update_fields=["verified_at", "updated_at"])

            # Activate user and set email_verified flag
            self.user.is_active = True
            self.user.email_verified = True
            self.user.save(update_fields=["is_active", "email_verified", "updated_at"])

            return True
        return False

    def __str__(self):
        status = "Verified" if self.is_verified() else "Pending"
        return f"{status} - {self.user.email}"
