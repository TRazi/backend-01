# apps/privacy/services.py
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from django.db import transaction
from django.utils import timezone

from apps.households.models import Household, Membership
from apps.transactions.models import Transaction
from apps.budgets.models import Budget
from apps.goals.models import Goal
from apps.accounts.models import Account
from apps.audit.services import log_action
from apps.users.models import User


class HouseholdAccessError(ValueError):
    """Raised when a user cannot access a given household."""

    pass


def _get_household_for_user(*, user: User, household_id: int) -> Household:
    try:
        household = Household.objects.get(id=household_id)
    except Household.DoesNotExist:
        raise HouseholdAccessError("Household not found")

    is_member = Membership.objects.filter(
        user=user,
        household=household,
        ended_at__isnull=True,
    ).exists()

    if not is_member:
        raise HouseholdAccessError("You must be a member of this household")

    return household


def _serialize_transaction(txn: Transaction) -> Dict[str, Any]:
    return {
        "id": txn.id,
        "amount": str(txn.amount),
        "description": txn.description,
        "status": txn.status,
        "transaction_type": txn.transaction_type,
        "date": txn.date.isoformat(),
        "merchant": txn.merchant,
        "transaction_source": txn.transaction_source,
        "account": txn.account_id,
        "category": txn.category_id,
        "goal": txn.goal_id,
        "budget": txn.budget_id,
        "is_recurring": txn.is_recurring,
        "created_at": txn.created_at.isoformat() if txn.created_at else None,
        "updated_at": txn.updated_at.isoformat() if txn.updated_at else None,
        "tags": list(txn.tags.values_list("id", flat=True)),
    }


def _serialize_budget(budget: Budget) -> Dict[str, Any]:
    return {
        "id": budget.id,
        "name": budget.name,
        "total_amount": str(budget.total_amount),
        "start_date": budget.start_date.isoformat() if budget.start_date else None,
        "end_date": budget.end_date.isoformat() if budget.end_date else None,
        "status": budget.status,
        "alert_threshold": str(budget.alert_threshold),
        "rollover_enabled": budget.rollover_enabled,
        "notes": budget.notes,
        "created_at": budget.created_at.isoformat() if budget.created_at else None,
        "updated_at": budget.updated_at.isoformat() if budget.updated_at else None,
    }


def _serialize_goal(goal: Goal) -> Dict[str, Any]:
    return {
        "id": goal.id,
        "name": goal.name,
        "description": goal.description,
        "target_amount": str(goal.target_amount),
        "current_amount": str(goal.current_amount),
        "due_date": goal.due_date.isoformat() if goal.due_date else None,
        "status": goal.status,
        "sticker_count": goal.sticker_count,
        "created_at": goal.created_at.isoformat() if goal.created_at else None,
        "updated_at": goal.updated_at.isoformat() if goal.updated_at else None,
    }


def _serialize_account(account: Account) -> Dict[str, Any]:
    return {
        "id": account.id,
        "name": getattr(account, "name", None),
        "account_type": getattr(account, "account_type", None),
        "balance": str(getattr(account, "balance", 0)),
        "institution_name": getattr(account, "institution_name", None),
        "last4": getattr(account, "last4", None),
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "updated_at": account.updated_at.isoformat() if account.updated_at else None,
    }


@transaction.atomic
def export_user_data(*, user: User, household_id: int) -> Dict[str, Any]:
    """
    Data export for a given user + household.
    This is what you return for "Download my data" / DSAR.
    """
    household = _get_household_for_user(user=user, household_id=household_id)

    # Core objects
    transactions = (
        Transaction.objects.filter(
            account__household=household,
        )
        .select_related("account", "category", "budget", "goal")
        .prefetch_related("tags")
    )

    budgets = Budget.objects.filter(household=household)
    goals = Goal.objects.filter(household=household)
    accounts = Account.objects.filter(household=household)

    # Membership info for this user
    membership_qs = Membership.objects.filter(
        user=user, household=household
    ).select_related("user", "household")
    membership = membership_qs.first()

    result = {
        "metadata": {
            "exported_at": timezone.now().isoformat(),
            "household_id": household.id,
            "household_name": household.name,
            "user_id": user.id,
            # Use BaseModel.created_at instead of date_joined in v2
            "user_created_at": (
                user.created_at.isoformat()
                if getattr(user, "created_at", None)
                else None
            ),
        },
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "locale": user.locale,
            "phone_number": user.phone_number,
            "role": user.role,
            "is_active": user.is_active,
        },
        "membership": {
            "id": membership.id if membership else None,
            "role": getattr(membership, "role", None) if membership else None,
            "created_at": (
                membership.created_at.isoformat()
                if membership and membership.created_at
                else None
            ),
        },
        "accounts": [_serialize_account(a) for a in accounts],
        "budgets": [_serialize_budget(b) for b in budgets],
        "goals": [_serialize_goal(g) for g in goals],
        "transactions": [_serialize_transaction(t) for t in transactions],
    }

    # Audit log
    log_action(
        user=user,
        household=household,
        action_type="EXPORT",
        action_description=f"Data export for household {household.name}",
        metadata={
            "exported_records": {
                "transactions": transactions.count(),
                "budgets": budgets.count(),
                "goals": goals.count(),
                "accounts": accounts.count(),
            }
        },
    )

    return result


# --- Deletion request / status -----------------------------

DATA_DELETION_STATUS_PENDING = "pending"
DATA_DELETION_STATUS_COMPLETED = "completed"
DATA_DELETION_STATUS_REJECTED = "rejected"


@transaction.atomic
def request_data_deletion(*, user: User) -> Dict[str, Any]:
    """
    Minimal implementation: mark the user as inactive, scrub some PII,
    and log the request. In a "real" setup you'd probably create a
    DataDeletionRequest model; you already have a v2 workflow in users/
    but this keeps a privacy app facade compatible with v1.
    """
    # Soft-delete style
    user.is_active = False
    # Don't destroy email (used as key) but you could mask names
    user.first_name = ""
    user.last_name = ""
    user.phone_number = ""
    user.save(
        update_fields=[
            "is_active",
            "first_name",
            "last_name",
            "phone_number",
            "updated_at",
        ]
    )

    log_action(
        user=user,
        household=None,
        action_type="DELETE",
        action_description=f"Data deletion requested for user {user.email}",
        metadata={
            "user_id": user.id,
            "timestamp": timezone.now().isoformat(),
            "action": "privacy_deletion_requested",
        },
    )

    return {
        "status": DATA_DELETION_STATUS_PENDING,
        "requested_at": timezone.now().isoformat(),
        "message": "Your deletion request has been recorded and your account has been disabled.",
    }


def get_data_deletion_status(*, user: User) -> Dict[str, Any]:
    """
    Very simple status function backed by user.is_active.
    If user is inactive -> treat as 'pending/completed' depending on how
    you want to word it for regulators.
    """
    if user.is_active:
        status = DATA_DELETION_STATUS_REJECTED
        message = "No active deletion request. Your account is currently active."
    else:
        status = DATA_DELETION_STATUS_COMPLETED
        message = (
            "Your account is disabled and queued for data retention/deletion policies."
        )

    return {
        "status": status,
        "checked_at": timezone.now().isoformat(),
        "message": message,
    }
