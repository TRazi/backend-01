# Audit Logging Quick Reference

## When to Log

**Always log:**
- ✅ User authentication (login, logout, failed attempts)
- ✅ Data modifications (create, update, delete)
- ✅ Permission/role changes
- ✅ Data exports
- ✅ Bulk operations
- ✅ Failed operations (with error details)

**Don't log:**
- ❌ Read-only operations (unless sensitive data)
- ❌ System health checks
- ❌ Static file requests

---

## Quick Examples

### Simple Action
```python
from audit.services import log_action

log_action(
    user=request.user,
    action_type='CREATE',
    action_description="Created new budget",
    request=request,
)
```

### Model Change
```python
from audit.services import log_model_change

log_model_change(
    user=request.user,
    action_type='UPDATE',
    instance=transaction,
    old_values={'amount': 50.00},
    request=request,
)
```

### Data Export
```python
from audit.services import log_data_export

log_data_export(
    user=request.user,
    export_type='transaction_export',
    record_count=150,
    request=request,
    household=household,
    file_format='csv',
)
```

---

## Action Types

- **AUTH**: LOGIN, LOGOUT, LOGIN_FAILED, PASSWORD_CHANGE, MFA_ENABLED
- **CRUD**: CREATE, UPDATE, DELETE, VIEW
- **DATA**: EXPORT, IMPORT, BULK_DELETE
- **PERMISSIONS**: PERMISSION_GRANT, PERMISSION_REVOKE, ROLE_CHANGE
- **SYSTEM**: RATE_LIMIT_EXCEEDED, ACCOUNT_LOCKED, ACCOUNT_UNLOCKED

---

## Service Layer Pattern
```python
from django.db import transaction
from audit.services import log_model_change

@transaction.atomic
def budget_create(*, household, amount, request):
    # 1. Create object
    budget = Budget.objects.create(
        household=household,
        amount=amount
    )
    
    # 2. Log action
    log_model_change(
        user=request.user,
        action_type='CREATE',
        instance=budget,
        request=request,
    )
    
    # 3. Return
    return budget
```

---

## DRF ViewSet Pattern
```python
from transactions.mixins import AuditLoggingMixin

class MyViewSet(AuditLoggingMixin, viewsets.ModelViewSet):
    # Automatic audit logging for all CRUD operations
    pass
```

---

## Viewing Audit Logs

**Admin Interface**: `/admin/audit/auditlog/`

**Filter by:**
- Action Type
- User
- Date Range
- Object Type
- Household

**Search by:**
- User email
- Description
- IP address