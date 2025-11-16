# apps/organisations/models.py
from django.db import models
from django.core.exceptions import ValidationError

from common.models import BaseModel
from organisations.enums import (
    ORGANISATION_TYPE_CHOICES,
    ORGANISATION_SUBSCRIPTION_CHOICES,
    ORG_BUDGET_CYCLE_CHOICES,
    CURRENCY_CHOICES,
    ORG_PAYMENT_STATUS_CHOICES,
)


class Organisation(BaseModel):
    """
    Represents an organisation for 'Whānau Works' memberships.

    Used for B2B and community use cases:
    - Corporate expense tracking
    - Educational institutions
    - Non-profits and clubs

    Key features:
    - Organisation-level billing (not per-member)
    - Owner has legal/billing responsibility
    - Multiple admins via Membership.role
    - Organisation-wide financial settings
    """

    # Basic information
    name = models.CharField(max_length=255, help_text="Organisation name")
    organisation_type = models.CharField(
        max_length=10,
        choices=ORGANISATION_TYPE_CHOICES,
        default="corp",
        help_text="Type of organisation",
    )
    contact_email = models.EmailField(
        help_text="Primary contact email for organisation"
    )

    # Owner/Primary Admin (legal and billing responsibility)
    owner = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,  # Prevent deletion of owner
        related_name="owned_organisations",
        help_text="Organisation owner (billing/legal contact)",
    )

    # Optional contact details
    phone_number = models.CharField(
        max_length=17, blank=True, help_text="Organisation contact phone"
    )
    address = models.TextField(blank=True, help_text="Physical address")
    website = models.URLField(blank=True, help_text="Organisation website")

    # Financial settings
    default_budget_cycle = models.CharField(
        max_length=1,
        choices=ORG_BUDGET_CYCLE_CHOICES,
        default="m",
        help_text="Default budget cycle for organisation",
    )
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default="NZD",
        help_text="Primary currency for organisation",
    )
    financial_year_start = models.CharField(
        max_length=5,
        default="01-01",
        help_text="Financial year start (MM-DD format, e.g., '04-01' for April 1st)",
    )

    # Subscription and billing (organisation-level)
    subscription_tier = models.CharField(
        max_length=20,
        choices=ORGANISATION_SUBSCRIPTION_CHOICES,
        default="ww_starter",
        help_text="Organisation subscription tier",
    )
    billing_cycle = models.CharField(
        max_length=1,
        choices=ORG_BUDGET_CYCLE_CHOICES,
        default="m",
        help_text="How often organisation is billed",
    )
    next_billing_date = models.DateField(
        null=True, blank=True, help_text="Next payment due date"
    )
    subscription_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Amount charged per billing cycle",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=ORG_PAYMENT_STATUS_CHOICES,
        default="trial",
        help_text="Current payment status",
    )

    # Capacity management
    is_active = models.BooleanField(
        default=True, help_text="Whether organisation account is active"
    )
    max_members = models.PositiveIntegerField(
        default=50, help_text="Maximum number of members allowed"
    )

    class Meta:
        db_table = "organisations"
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["is_active", "payment_status"]),
            models.Index(fields=["owner"]),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Validate financial_year_start format."""
        super().clean()

        if self.financial_year_start:
            try:
                month, day = self.financial_year_start.split("-")
                month, day = int(month), int(day)

                if not (1 <= month <= 12 and 1 <= day <= 31):
                    raise ValueError
            except (ValueError, AttributeError):
                raise ValidationError(
                    "financial_year_start must be in MM-DD format (e.g., '04-01')"
                )

    @property
    def current_member_count(self) -> int:
        """Get current number of active members."""
        return self.memberships.filter(status="active").count()

    @property
    def has_capacity(self) -> bool:
        """Check if organisation can accept more members."""
        return self.current_member_count < self.max_members

    @property
    def is_trial(self) -> bool:
        """Check if organisation is in trial period."""
        return self.payment_status == "trial"

    @property
    def is_paid_up(self) -> bool:
        """Check if organisation subscription is in good standing."""
        return self.payment_status == "active"
