# Test Failures Fix Guide

## Summary
42 test failures across 6 categories. All are fixable configuration/compatibility issues.

---

## Category 1: UUID/ID Serializer Mismatches (14 failures)

**Root Cause**: Models use `uuid` for API but tests expect `id` field in responses.

**Affected Tests**:
- `test_household_serializer` - KeyError: 'id'
- `test_household_serializer_with_multiple_fields` - assert 'id' in data
- `test_transaction_tag_serializer` - assert 'id' in data

**Solution**: Add `id` field to serializers or update tests to use `uuid`.

### Option A: Add `id` to serializer fields (backward compatible)
```python
# apps/households/serializers.py
class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = [
            "id",        # ADD THIS
            "uuid",
            "name",
            # ... rest
        ]
```

### Option B: Update tests to use `uuid` instead of `id`
```python
# Change this:
assert data["id"] == household.id
# To this:
assert data["uuid"] == str(household.uuid)
```

**Recommendation**: Option A (add both `id` and `uuid` to fields) for backward compatibility.

---

## Category 2: ViewSet Routing - 404 Errors (11 failures)

**Root Cause**: ViewSets declare `lookup_field = "uuid"` but tests/URLs use numeric IDs.

**Affected Tests**:
- All update tests (404 instead of 200)
- All delete tests (404 instead of 204)
- Custom actions (close_account, link_transfer, etc.)

**Files to Fix**:
- `apps/accounts/viewsets.py`
- `apps/transactions/viewsets.py`
- `apps/households/apis.py`

**Solution**: Choose one approach consistently:

### Option A: Use UUID in tests (recommended for production)
```python
# Test code should use:
response = client.patch(f"/api/v1/accounts/{account.uuid}/")
```

### Option B: Change ViewSet to use `id` lookup
```python
class AccountViewSet(viewsets.ModelViewSet):
    lookup_field = "id"  # Changed from "uuid"
```

**Recommendation**: Option A - Update tests to use UUID (more secure, prevents enumeration).

---

## Category 3: Household Create Validation (2 failures)

**Root Cause**: Tests don't provide required `household_type` and `budget_cycle`.

**Affected Tests**:
- `test_create_household_authenticated` - 400 instead of 201
- `test_create_household_uses_create_serializer` - 400 instead of 201

**Fix**: Update test data to include required fields:
```python
# apps/households/tests/test_household_apis.py
data = {
    "name": "New Household",
    "household_type": "fam",    # ADD
    "budget_cycle": "m",        # ADD
}
```

---

## Category 4: Decimal Formatting in Reports (4 failures)

**Root Cause**: Decimal fields return `"150.00"` but tests expect `"150"`.

**Affected Tests**:
- All `test_generate_spending_report_*` tests

**Fix Options**:

### Option A: Update test assertions
```python
# Change:
assert result['total'] == '150'
# To:
assert result['total'] == '150.00'
```

### Option B: Add custom serializer field
```python
from rest_framework import serializers

class MoneyField(serializers.DecimalField):
    def to_representation(self, value):
        if value == int(value):
            return str(int(value))
        return str(value)
```

**Recommendation**: Option A - Tests should match actual decimal format.

---

## Category 5: MFA Error Messages (4 failures)

**Root Cause**: Error response format changed.

**Affected Tests**:
- `test_mfa_enabled_requires_code`
- `test_mfa_enabled_invalid_otp_fails`
- `test_mfa_enabled_invalid_backup_code_fails`
- `test_blank_otp_and_backup_code_fails`

**Fix**: Update test assertions to match new error format:
```python
# apps/users/tests/test_mfa_serializers.py

# OLD:
assert 'MFA code required' in str(errors)

# NEW:
assert 'mfa_required' in str(errors) or 'MFA code required' in str(errors)
```

Or update serializer to match expected format.

---

## Category 6: User Manager Validation Messages (3 failures)

**Root Cause**: Username login feature changed validation message.

**Affected Tests**:
- `test_create_user_without_email_raises_error`
- `test_create_user_with_none_email_raises_error`
- `test_create_superuser_without_email_raises_error`

**Current Message**: "Either email or username must be provided"
**Expected Message**: "The Email field must be set"

**Fix**: Update tests to match new validation logic:
```python
# apps/users/tests/test_user_managers.py

with pytest.raises(ValueError) as exc_info:
    User.objects.create_user(email="", password="pass123")

# OLD:
assert 'The Email field must be set' in str(exc_info.value)

# NEW:
assert 'Either email or username must be provided' in str(exc_info.value)
```

---

## Category 7: Transaction Tag Missing UUID (1 failure)

**Root Cause**: `TransactionTagSerializer` doesn't expose `uuid` field.

**Fix**:
```python
# apps/transactions/serializers.py
class TransactionTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransactionTag
        fields = ["uuid", "name", "color", "created_at", "updated_at"]  # Add uuid
        read_only_fields = ["uuid", "created_at", "updated_at"]
```

---

## Category 8: User Admin Field Changes (4 failures)

**Root Cause**: Admin class fields changed after username feature added.

**Fix**: Update test expectations in `apps/users/tests/test_admin.py`:

```python
# Test should expect current admin configuration
expected_list_display = ['email', 'username', 'first_name', 'last_name', ...]
expected_search_fields = ['email', 'username', 'first_name', ...]
expected_readonly = ['uuid', 'created_at', 'updated_at', 'last_login']
```

---

## Category 9: Test Utility - Invalid Enum Value (1 failure)

**Root Cause**: Test uses invalid household_type value.

**Fix**:
```python
# apps/common/tests/test_test_utils.py

# Change 'sch' to valid value like 'edu' or 'fam'
household = create_test_household(household_type="fam")
```

---

## Category 10: Audit Service False Positive (1 failure)

**Root Cause**: Service detecting changes when there are none.

**Needs Investigation**: Check `apps/audit/services.py` for field comparison logic.

---

## Quick Fix Priority

### High Priority (Breaks API functionality):
1. **Category 2** - Fix 404 routing issues
2. **Category 3** - Fix household creation validation

### Medium Priority (Test expectations):
3. **Category 1** - Add id/uuid to serializers
4. **Category 7** - Add uuid to TransactionTagSerializer
5. **Category 5** - Update MFA error messages
6. **Category 6** - Update user manager error messages

### Low Priority (Cosmetic):
7. **Category 4** - Decimal formatting
8. **Category 8** - Admin field expectations
9. **Category 9** - Test utility enum value
10. **Category 10** - Audit service investigation

---

## Recommended Approach

1. **Run each category separately** to verify fixes:
   ```bash
   pytest apps/households/tests/test_household_serializers.py -v
   pytest apps/accounts/tests/test_account_viewsets.py::TestAccountViewSetUpdate -v
   ```

2. **Update tests first** (safer than changing production code)

3. **Verify no regressions** after each fix

4. **Document API changes** if modifying serializer fields
