"""
Audit logging usage examples.
Reference guide for implementing audit logging across the application.
"""

from django.http import HttpRequest
from audit.services import log_action, log_model_change, log_data_export


# ============================================================================
# Example 1: Basic Action Logging
# ============================================================================


def example_basic_logging(request: HttpRequest, user):
    """Log a simple action without a specific object."""
    from audit.services import log_action

    log_action(
        user=user,
        action_type="LOGIN",
        action_description=f"User {user.email} logged in successfully",
        request=request,
    )


# ============================================================================
# Example 2: CREATE Action (New Transaction)
# ============================================================================


def example_create_transaction(request: HttpRequest, transaction):
    """Log transaction creation."""
    from audit.services import log_model_change

    log_model_change(
        user=request.user,
        action_type="CREATE",
        instance=transaction,
        request=request,
    )

    # Or with custom description:
    log_model_change(
        user=request.user,
        action_type="CREATE",
        instance=transaction,
        request=request,
        description=f"Created transaction: {transaction.description} for ${transaction.amount}",
    )


# ============================================================================
# Example 3: UPDATE Action with Change Tracking
# ============================================================================


def example_update_transaction(
    request: HttpRequest, transaction_id: int, new_data: dict
):
    """Log transaction update with before/after values."""
    from transactions.models import Transaction
    from audit.services import log_model_change

    # Get existing transaction
    transaction = Transaction.objects.get(pk=transaction_id)

    # Capture old values BEFORE making changes
    old_values = {
        "amount": transaction.amount,
        "description": transaction.description,
        "category": transaction.category,
    }

    # Make changes
    transaction.amount = new_data.get("amount", transaction.amount)
    transaction.description = new_data.get("description", transaction.description)
    transaction.category = new_data.get("category", transaction.category)
    transaction.save()

    # Log with change tracking
    log_model_change(
        user=request.user,
        action_type="UPDATE",
        instance=transaction,
        old_values=old_values,
        request=request,
    )


# ============================================================================
# Example 4: DELETE Action
# ============================================================================


def example_delete_budget(request: HttpRequest, budget):
    """Log budget deletion."""
    from audit.services import log_model_change

    # Log BEFORE deleting (so we still have the instance data)
    log_model_change(
        user=request.user,
        action_type="DELETE",
        instance=budget,
        request=request,
    )

    # Now delete
    budget.delete()


# ============================================================================
# Example 5: Permission/Role Changes
# ============================================================================


def example_role_change(request: HttpRequest, membership, old_role: str, new_role: str):
    """Log membership role change."""
    from audit.services import log_action

    log_action(
        user=request.user,
        action_type="ROLE_CHANGE",
        action_description=f"Changed {membership.user.email} role from {old_role} to {new_role}",
        request=request,
        object_type="Membership",
        object_id=membership.pk,
        object_repr=str(membership),
        household=membership.household,
        changes={
            "role": {
                "old": old_role,
                "new": new_role,
            }
        },
    )


# ============================================================================
# Example 6: Data Export Logging
# ============================================================================


def example_transaction_export(request: HttpRequest, household, transactions):
    """Log transaction export."""
    from audit.services import log_data_export
    from datetime import date

    log_data_export(
        user=request.user,
        export_type="transaction_export",
        record_count=len(transactions),
        request=request,
        household=household,
        date_range_start=date(2024, 1, 1),
        date_range_end=date(2024, 12, 31),
        file_format="csv",
        file_size_bytes=1024 * 50,  # 50 KB
        export_filters={
            "category": "Groceries",
            "min_amount": 10.00,
        },
    )


# ============================================================================
# Example 7: Failed Action Logging
# ============================================================================


def example_failed_action(request: HttpRequest, user):
    """Log a failed action with error message."""
    from audit.services import log_action

    try:
        # Some operation that might fail
        raise PermissionError("User does not have permission to delete this budget")
    except Exception as e:
        log_action(
            user=user,
            action_type="DELETE",
            action_description="Attempted to delete budget",
            request=request,
            object_type="Budget",
            object_id=123,
            success=False,
            error_message=str(e),
        )


# ============================================================================
# Example 8: System Action (No User)
# ============================================================================


def example_system_action():
    """Log an automated system action."""
    from audit.services import log_action

    log_action(
        user=None,  # System action
        action_type="DELETE",
        action_description="System: Cleaned up expired sessions",
        metadata={
            "expired_sessions_count": 42,
            "cleanup_type": "scheduled",
        },
    )


# ============================================================================
# Example 9: Bulk Operations
# ============================================================================


def example_bulk_delete(request: HttpRequest, deleted_count: int):
    """Log bulk deletion."""
    from audit.services import log_action

    log_action(
        user=request.user,
        action_type="BULK_DELETE",
        action_description=f"Bulk deleted {deleted_count} transactions",
        request=request,
        object_type="Transaction",
        household=request.household,
        metadata={
            "count": deleted_count,
            "filters_applied": {
                "date_before": "2023-01-01",
            },
        },
    )
