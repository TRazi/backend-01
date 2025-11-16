"""
Audit logging service layer.
Provides utilities for creating audit records throughout the application.
"""

from typing import Optional, Dict, Any
from django.http import HttpRequest
from django.contrib.auth import get_user_model
from django.db import transaction

from audit.models import AuditLog, DataExportLog
from audit.enums import ACTION_CHOICES


def get_user_model_lazy():
    from django.contrib.auth import get_user_model

    return get_user_model()


User = get_user_model_lazy()


def _get_ip_address(request: Optional[HttpRequest]) -> Optional[str]:
    """Extract IP address from request, handling proxies."""
    if not request:
        return None

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def _get_user_agent(request: Optional[HttpRequest]) -> str:
    """Extract user agent from request."""
    if not request:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")


def _get_request_context(request: Optional[HttpRequest]) -> Dict[str, Any]:
    """Extract common request context for audit logging."""
    if not request:
        return {
            "ip_address": None,
            "user_agent": "",
            "request_path": "",
            "request_method": "",
        }

    return {
        "ip_address": _get_ip_address(request),
        "user_agent": _get_user_agent(request),
        "request_path": request.path,
        "request_method": request.method,
    }


def log_action(
    *,
    user: Optional[User],
    action_type: str,
    action_description: str,
    request: Optional[HttpRequest] = None,
    object_type: str = "",
    object_id: Optional[int] = None,
    object_repr: str = "",
    household=None,
    organisation=None,
    changes: Optional[Dict] = None,
    metadata: Optional[Dict] = None,
    success: bool = True,
    error_message: str = "",
) -> AuditLog:
    """
    Create an audit log entry.

    Args:
        user: User performing the action (None for system actions)
        action_type: Type of action from ACTION_CHOICES
        action_description: Human-readable description
        request: HTTP request object (for extracting context)
        object_type: Model name of affected object
        object_id: Primary key of affected object
        object_repr: String representation of affected object
        household: Household context (if applicable)
        organisation: Organisation context (if applicable)
        changes: Dictionary of field changes for UPDATE actions
        metadata: Additional contextual data
        success: Whether action was successful
        error_message: Error message if action failed

    Returns:
        AuditLog: Created audit log entry

    Example:
        log_action(
            user=request.user,
            action_type='CREATE',
            action_description=f"Created transaction: {transaction.description}",
            request=request,
            object_type='Transaction',
            object_id=transaction.id,
            object_repr=str(transaction),
            household=transaction.household,
        )
    """
    # Validate action_type
    valid_actions = [choice[0] for choice in ACTION_CHOICES]
    if action_type not in valid_actions:
        raise ValueError(
            f"Invalid action_type: {action_type}. Must be one of {valid_actions}"
        )

    # Extract request context
    request_context = _get_request_context(request)

    # Create audit log entry
    return AuditLog.objects.create(
        user=user,
        action_type=action_type,
        action_description=action_description,
        object_type=object_type,
        object_id=object_id,
        object_repr=object_repr,
        household=household,
        organisation=organisation,
        changes=changes or {},
        metadata=metadata or {},
        success=success,
        error_message=error_message,
        **request_context,
    )


def log_event(*args, **kwargs):
    """
    Backwards-compatible entry point for audit logging.

    Used by:
      - users.apis (auth-related events)
      - config security / rate-limit tests
      - legacy privacy/reports flows (if adapted)

    It delegates to log_action() if present, otherwise becomes a no-op.
    This keeps imports and calls from blowing up while you evolve the
    audit subsystem.
    """
    fn = globals().get("log_action")
    if callable(fn):
        return fn(*args, **kwargs)
    # Temporary no-op fallback: don't break auth/admin just because
    # audit plumbing isn't finished.
    return None


def _build_action_description(action_type: str, model_name: str, instance) -> str:
    """Build default description for model action."""
    action_templates = {
        "CREATE": "Created",
        "UPDATE": "Updated",
        "DELETE": "Deleted",
    }
    action_verb = action_templates.get(action_type, action_type)
    return f"{action_verb} {model_name}: {str(instance)}"


def _calculate_field_changes(instance, old_values: Dict) -> Dict:
    """Calculate changes between old and new field values."""
    changes = {}
    for field, old_value in old_values.items():
        new_value = getattr(instance, field, None)
        if old_value != new_value:
            changes[field] = {
                "old": str(old_value) if old_value is not None else None,
                "new": str(new_value) if new_value is not None else None,
            }
    return changes


def log_model_change(
    *,
    user: Optional[User],
    action_type: str,
    instance,
    old_values: Optional[Dict] = None,
    request: Optional[HttpRequest] = None,
    description: Optional[str] = None,
) -> AuditLog:
    """
    Log a model change (CREATE, UPDATE, DELETE).

    Args:
        user: User performing the action
        action_type: 'CREATE', 'UPDATE', or 'DELETE'
        instance: Model instance being changed
        old_values: Dictionary of old field values (for UPDATE)
        request: HTTP request object
        description: Override default description

    Returns:
        AuditLog: Created audit log entry

    Example:
        # Before update
        old_values = {
            'amount': transaction.amount,
            'description': transaction.description,
        }

        # After update
        log_model_change(
            user=request.user,
            action_type='UPDATE',
            instance=transaction,
            old_values=old_values,
            request=request,
        )
    """
    model_name = instance.__class__.__name__

    # Build description
    if not description:
        description = _build_action_description(action_type, model_name, instance)

    # Calculate changes for UPDATE
    changes = {}
    if action_type == "UPDATE" and old_values:
        changes = _calculate_field_changes(instance, old_values)

    # Extract household context if available
    household = getattr(instance, "household", None)
    organisation = getattr(instance, "organisation", None)

    return log_action(
        user=user,
        action_type=action_type,
        action_description=description,
        request=request,
        object_type=model_name,
        object_id=instance.pk,
        object_repr=str(instance),
        household=household,
        organisation=organisation,
        changes=changes,
    )


def log_data_export(
    *,
    user: User,
    export_type: str,
    record_count: int,
    request: HttpRequest,
    household=None,
    date_range_start=None,
    date_range_end=None,
    file_format: str = "json",
    file_size_bytes: Optional[int] = None,
    export_filters: Optional[Dict] = None,
) -> DataExportLog:
    """
    Log a data export operation.

    Args:
        user: User requesting the export
        export_type: Type of export from EXPORT_TYPE_CHOICES
        record_count: Number of records exported
        request: HTTP request object
        household: Household context (if applicable)
        date_range_start: Start date of export range
        date_range_end: End date of export range
        file_format: Export file format
        file_size_bytes: Size of export file
        export_filters: Filters applied to export

    Returns:
        DataExportLog: Created export log entry

    Example:
        log_data_export(
            user=request.user,
            export_type='transaction_export',
            record_count=150,
            request=request,
            household=household,
            date_range_start=start_date,
            date_range_end=end_date,
            file_format='csv',
        )
    """
    # Also create general audit log
    log_action(
        user=user,
        action_type="EXPORT",
        action_description=f"Exported {record_count} records ({export_type})",
        request=request,
        household=household,
        metadata={
            "export_type": export_type,
            "record_count": record_count,
            "file_format": file_format,
        },
    )

    # Create specific export log
    return DataExportLog.objects.create(
        user=user,
        export_type=export_type,
        household=household,
        record_count=record_count,
        date_range_start=date_range_start,
        date_range_end=date_range_end,
        ip_address=_get_ip_address(request),
        user_agent=_get_user_agent(request),
        file_format=file_format,
        file_size_bytes=file_size_bytes,
        export_filters=export_filters or {},
    )


def get_model_field_changes(instance, old_instance) -> Dict[str, Dict[str, Any]]:
    """
    Compare two model instances and return changed fields.

    Args:
        instance: New/current instance
        old_instance: Previous instance

    Returns:
        Dictionary of changes: {field: {'old': value, 'new': value}}

    Example:
        old_transaction = Transaction.objects.get(pk=transaction.pk)
        # ... make changes ...
        transaction.save()
        changes = get_model_field_changes(transaction, old_transaction)
    """
    changes = {}

    for field in instance._meta.fields:
        field_name = field.name
        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(instance, field_name, None)

        # Skip unchanged fields
        if old_value == new_value:
            continue

        # Skip auto-generated fields
        if field_name in ["id", "created_at", "updated_at"]:
            continue

        changes[field_name] = {
            "old": str(old_value) if old_value is not None else None,
            "new": str(new_value) if new_value is not None else None,
        }

    return changes
