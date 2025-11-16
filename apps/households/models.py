# apps/households/models.py
import uuid
from typing import Optional

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from common.models import BaseModel
from households.enums import (
    HOUSEHOLD_TYPE_CHOICES,
    BUDGET_CYCLE_CHOICES,
    MEMBERSHIP_TYPE_CHOICES,
    MEMBERSHIP_STATUS_CHOICES,
    PAYMENT_STATUS_CHOICES,
)
from users.enums import ROLE_CHOICES


class Household(BaseModel):
    """
    Represents a household - the main tenant unit in the system.
    Each household can have multiple users via Membership.

    Key identifiers:
    - id: Internal database key
    - uuid: External API identifier (prevents enumeration)
    """

    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Unique identifier for API and external integrations",
    )

    name = models.CharField(max_length=255)
    household_type = models.CharField(
        max_length=10, choices=HOUSEHOLD_TYPE_CHOICES, default="fam"
    )
    budget_cycle = models.CharField(
        max_length=1, choices=BUDGET_CYCLE_CHOICES, default="m"
    )

    class Meta:
        db_table = "households"
        verbose_name = "Household"
        verbose_name_plural = "Households"
        indexes = [
            models.Index(fields=["uuid"]),
        ]

    def __str__(self):
        return self.name


class Membership(BaseModel):
    """
    Links users to households/organisations with subscription and permission details.

    Key features:
    - Users can have multiple memberships (family + student flat + org)
    - User.household points to PRIMARY household
    - Tracks subscription tier + permission role
    - Supports billing for organisational memberships

    Test Suite Requirements:
    - Must expose is_active BOOLEAN (used heavily in privacy/tests)
    - Must expose ended_at (NOT end_date)
    - Must track start_date for auditability
    """

    # Core relationships
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    household = models.ForeignKey(
        "Household",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organisation = models.ForeignKey(
        "organisations.Organisation",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="memberships",
        help_text="Optional / Whānau Works memberships",
    )

    # Subscription tier + role
    membership_type = models.CharField(
        max_length=2,
        choices=MEMBERSHIP_TYPE_CHOICES,
        default="sw",
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="observer",
    )

    # Status (string), required by business logic
    status = models.CharField(
        max_length=20,
        choices=MEMBERSHIP_STATUS_CHOICES,
        default="active",
    )

    # Tests require a BOOLEAN field
    is_active = models.BooleanField(
        default=True,
        help_text="Boolean mirror of status='active'. Tests filter heavily on this.",
    )

    # Tests expect this exact field name
    start_date = models.DateTimeField(
        auto_now_add=True,
        help_text="When user joined this household",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Auto-set when membership is cancelled/expired",
    )

    # Primary household selector
    is_primary = models.BooleanField(
        default=False,
        help_text="User may only have one primary household",
    )

    # Optional org-level billing
    billing_cycle = models.CharField(
        max_length=1,
        choices=BUDGET_CYCLE_CHOICES,
        null=True,
        blank=True,
    )
    next_billing_date = models.DateField(
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "memberships"
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"
        unique_together = [["user", "household"]]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["household", "is_active"]),
            models.Index(fields=["user", "is_primary"]),
            models.Index(fields=["is_active", "ended_at"]),
        ]
        ordering = ["-is_primary", "-created_at"]

    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return (
            f"{self.user.email} - {self.household.name} "
            f"({self.get_membership_type_display()}){primary}"
        )

    # ---------- Validation ----------
    def clean(self):
        """Enforce membership rules."""
        super().clean()

        # Membership type cannot be blank on active memberships
        if self.status == "active" and not self.membership_type:
            raise ValidationError(
                "Active memberships must have a membership type assigned. "
                f"Valid options: {dict(MEMBERSHIP_TYPE_CHOICES)}"
            )

        # Membership type must be a valid choice
        valid_types = [code for code, label in MEMBERSHIP_TYPE_CHOICES]
        if self.membership_type and self.membership_type not in valid_types:
            raise ValidationError(
                f"Invalid membership type '{self.membership_type}'. "
                f"Valid options: {', '.join(valid_types)}"
            )

        # Prevent primary assignment when inactive
        if self.is_primary and self.status != "active":
            raise ValidationError("Only active memberships can be set as primary")

        # Ensure only ONE primary per user
        if self.is_primary:
            existing = Membership.objects.filter(
                user=self.user, is_primary=True
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError(
                    "User already has a primary household. "
                    "Use the membership_set_primary service."
                )

    # ---------- Save Logic ----------
    def save(self, *args, **kwargs):
        # Keep is_active boolean aligned with status
        self.is_active = self.status == "active"

        # Auto-set ended_at only once
        if self.status in ["cancelled", "expired"] and not self.ended_at:
            self.ended_at = timezone.now()

        super().save(*args, **kwargs)

    # ---------- Convenience Properties ----------
    @property
    def is_active_membership(self) -> bool:
        """Alias for status check (legacy compatibility)."""
        return self.is_active

    @property
    def days_until_end(self) -> Optional[int]:
        if not self.ended_at:
            return None
        delta = self.ended_at - timezone.now()
        return max(0, delta.days)
