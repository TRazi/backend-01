# apps/accounts/models.py
import uuid
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

from apps.common.models import BaseModel
from apps.accounts.enums import ACCOUNT_TYPE_CHOICES


class Account(BaseModel):
    """
    Financial account belonging to a household.

    Key identifiers:
    - id: Internal database key
    - uuid: External API identifier (prevents enumeration, enables integrations)

    This model must align with:
    - test suite expectations
    - transaction household scoping
    - serializers and viewsets using `name`, `institution`, etc
    """

    uuid = models.UUIDField(
        unique=True,
        default=uuid.uuid4,
        editable=False,
        db_index=True,
        help_text="Unique identifier for API and bank integrations",
    )

    household = models.ForeignKey(
        "households.Household",
        on_delete=models.CASCADE,
        related_name="accounts",
    )

    # Required by tests + serializers
    name = models.CharField(max_length=255)

    institution = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Bank or provider name (optional)",
    )

    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="checking",
    )

    currency = models.CharField(
        max_length=10, default="NZD", help_text="Store ISO currency code"
    )

    include_in_totals = models.BooleanField(
        default=True, help_text="Whether to include this account in balance summaries"
    )

    # Financial fields
    balance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    available_credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For credit accounts",
    )

    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For credit accounts",
    )

    class Meta:
        db_table = "accounts"
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        indexes = [
            models.Index(fields=["uuid"]),
            models.Index(fields=["household", "account_type"]),
            models.Index(fields=["household", "include_in_totals"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.household.name})"

    @property
    def calculated_balance(self):
        """
        Dynamic balance property for future reconciliation logic.
        """
        return self.balance
