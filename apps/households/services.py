# apps/households/services.py
from typing import Optional
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from households.models import Membership, Household


def get_user_model_lazy():
    from django.contrib.auth import get_user_model

    return get_user_model()


User = get_user_model_lazy()


@transaction.atomic
def membership_set_primary(*, membership: Membership) -> Membership:
    """
    Set a membership as primary for the user.
    Automatically unsets any existing primary membership.
    Syncs User.household and User.role.

    Args:
        membership: Membership instance to set as primary

    Returns:
        Membership: Updated membership instance

    Raises:
        ValidationError: If membership is not active
    """
    if membership.status != "active":
        raise ValidationError("Only active memberships can be set as primary")

    # Unset existing primary for this user
    Membership.objects.filter(user=membership.user, is_primary=True).exclude(
        pk=membership.pk
    ).update(is_primary=False)

    # Set this membership as primary
    membership.is_primary = True
    membership.save(update_fields=["is_primary", "updated_at"])

    # Sync User fields
    membership.user.household = membership.household
    membership.user.role = membership.role
    membership.user.save(update_fields=["household", "role", "updated_at"])

    return membership


@transaction.atomic
def membership_create(
    *,
    user: User,
    household: Household,
    membership_type: str,
    role: str,
    is_primary: bool = False,
    organisation=None,
) -> Membership:
    """
    Create a new membership for a user.

    Args:
        user: User to add to household
        household: Household to join
        membership_type: Subscription tier (sw, fw, mm, wp, ww, if)
        role: Permission level (admin, parent, teen, child, flatmate, observer)
        is_primary: Whether this should be the primary household
        organisation: Optional organisation link

    Returns:
        Membership: Created membership instance

    Raises:
        ValidationError: If user already member of household
    """
    # Check if membership already exists
    if Membership.objects.filter(user=user, household=household).exists():
        raise ValidationError("User is already a member of this household")

    membership = Membership(
        user=user,
        household=household,
        organisation=organisation,
        membership_type=membership_type,
        role=role,
        status="active",
        is_primary=is_primary,
    )

    membership.full_clean()
    membership.save()

    # Set as primary if requested
    if is_primary:
        membership_set_primary(membership=membership)

    return membership


@transaction.atomic
def membership_deactivate(
    *, membership: Membership, status: str = "cancelled"
) -> Membership:
    """
    Deactivate a membership and handle cleanup.

    Args:
        membership: Membership to deactivate
        status: New status (cancelled or expired)

    Returns:
        Membership: Updated membership instance
    """
    if status not in ["cancelled", "expired", "inactive"]:
        raise ValidationError(f"Invalid deactivation status: {status}")

    membership.status = status
    membership.ended_at = timezone.now()

    # If this was primary, unset it
    was_primary = membership.is_primary
    if was_primary:
        membership.is_primary = False

    membership.save(update_fields=["status", "ended_at", "is_primary", "updated_at"])

    # If was primary, try to set another membership as primary
    if was_primary:
        new_primary = (
            Membership.objects.filter(user=membership.user, status="active")
            .order_by("-created_at")
            .first()
        )

        if new_primary:
            membership_set_primary(membership=new_primary)
        else:
            # No active memberships left, clear User.household
            membership.user.household = None
            membership.user.role = "observer"
            membership.user.save(update_fields=["household", "role", "updated_at"])

    return membership
