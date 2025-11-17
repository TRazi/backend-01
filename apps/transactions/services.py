"""
Transaction service layer with integrated audit logging.
"""

from typing import Optional, Dict, Any
from decimal import Decimal
from django.db import transaction
from django.http import HttpRequest

from apps.transactions.models import Transaction
from apps.audit.services import log_model_change


@transaction.atomic
def transaction_create(
    *,
    account,
    amount: Decimal,
    description: str,
    request: HttpRequest,
    category=None,
    transaction_date=None,
    **kwargs,
) -> Transaction:
    """
    Create a new transaction with audit logging.

    Args:
        account: Account for the transaction
        amount: Transaction amount
        description: Transaction description
        request: HTTP request object
        category: Optional category
        transaction_date: Optional date (defaults to today)
        **kwargs: Additional transaction fields

    Returns:
        Transaction: Created transaction instance
    """
    # Create transaction
    trans = Transaction(
        account=account,
        amount=amount,
        description=description,
        category=category,
        date=transaction_date,
        **kwargs,
    )
    trans.full_clean()
    trans.save()

    # Update account balance (if needed)
    account.balance += amount
    account.save(update_fields=["balance"])

    # Audit logging
    log_model_change(
        user=request.user,
        action_type="CREATE",
        instance=trans,
        request=request,
        description=f"Created transaction: {description} for ${amount}",
    )

    return trans


@transaction.atomic
def transaction_update(
    *, transaction_id: int, request: HttpRequest, **update_fields
) -> Transaction:
    """
    Update a transaction with audit logging.

    Args:
        transaction_id: ID of transaction to update
        request: HTTP request object
        **update_fields: Fields to update

    Returns:
        Transaction: Updated transaction instance
    """
    # Get transaction
    trans = Transaction.objects.get(pk=transaction_id)

    # Capture old values for audit
    old_values = {
        field: getattr(trans, field)
        for field in update_fields.keys()
        if hasattr(trans, field)
    }

    # Update fields
    for field, value in update_fields.items():
        setattr(trans, field, value)

    trans.full_clean()
    trans.save()

    # Audit logging
    log_model_change(
        user=request.user,
        action_type="UPDATE",
        instance=trans,
        old_values=old_values,
        request=request,
    )

    return trans


@transaction.atomic
def transaction_delete(
    *,
    transaction_id: int,
    request: HttpRequest,
) -> None:
    """
    Delete a transaction with audit logging.

    Args:
        transaction_id: ID of transaction to delete
        request: HTTP request object
    """
    trans = Transaction.objects.get(pk=transaction_id)

    # Audit logging BEFORE deletion
    log_model_change(
        user=request.user,
        action_type="DELETE",
        instance=trans,
        request=request,
    )

    # Update account balance (reverse transaction)
    if trans.account:
        trans.account.balance -= trans.amount
        trans.account.save(update_fields=["balance"])

    # Delete transaction
    trans.delete()
