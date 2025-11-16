# User Identification & Duplicate Prevention - Implementation Summary

## Overview
Comprehensive measures have been implemented to ensure unique user identification and prevent duplicate accounts in the KinWise system.

## Implementation Details

### 1. **Multiple Unique Identifiers**

#### Primary Key (Database ID)
- Type: `bigint` (auto-incrementing)
- Constraint: Primary key, unique at database level
- Usage: Internal database reference
- Value: Sequential (1, 2, 3, ...)

#### UUID (Universal Unique Identifier)
- Type: UUIDField (RFC 4122 compliant)
- Constraint: Unique at database level
- Index: `users_uuid_7a3bf894_uniq`
- Usage: External API references, prevents ID enumeration attacks
- Value: Cryptographically random (e.g., `5289f1bd-4ae0-43f2-b80e-86f259269184`)
- Migration: `0004_add_uuid_field.py` (with automatic UUID generation for existing users)

#### Email Address
- Type: EmailField (unique)
- Constraint: Unique at database level
- Index: `users_email_key`, `users_email_a7cfd1_idx`, `users_email_0ea73cca_like`
- Usage: Authentication identifier, login method
- Normalization: Automatically converted to lowercase

### 2. **Database-Level Constraints**

Two unique constraints protect against duplicates:

```sql
CONSTRAINT users_email_key UNIQUE (email)
CONSTRAINT users_uuid_7a3bf894_uniq UNIQUE (uuid)
```

These constraints prevent database-level insertion of duplicate records, making it impossible to create duplicate users even if application logic fails.

### 3. **Indexes for Uniqueness & Performance**

- `users_pkey`: Primary key index on `id`
- `users_email_key`: Unique index on `email`
- `users_uuid_7a3bf894_uniq`: Unique index on `uuid`
- `users_email_a7cfd1_idx`: Composite index on `(email, is_active)` for query optimization
- `users_email_0ea73cca_like`: Pattern matching index for email searches
- `users_uuid_4cb658_idx`: Regular index on `uuid` for faster lookups

### 4. **Rate Limiting on Account Creation**

Prevents automated account creation attacks and abuse.

**Methods:**

```python
# Check if IP address has exceeded creation limit
if User.check_creation_rate_limit(ip_address):
    raise RateLimitExceeded("Too many accounts from this IP")

# Create user
new_user = User.objects.create_user(email=email, password=password)

# Increment counter for this IP
User.increment_creation_rate_limit(ip_address)
```

**Default Settings:**
- Maximum accounts: 5 per IP address
- Time window: 3600 seconds (1 hour)
- Storage: Django cache (configurable)

**Implementation Location:**
- `User.check_creation_rate_limit(ip_address, max_accounts=5, window_seconds=3600)`
- `User.increment_creation_rate_limit(ip_address, window_seconds=3600)`

**Integration Point:**
Should be called in the user registration view before creating an account.

### 5. **Email Verification Enforcement**

Ensures users verify their email before accessing sensitive features.

**Method:**

```python
if not user.is_email_verified_for_action():
    raise PermissionDenied("Email must be verified for this action")
```

**Current Status:**
- Verified: 33/34 users
- Unverified: 1/34 users
- Field: `email_verified` (BooleanField, default=False)
- Verification Logic: In `EmailVerification` model

### 6. **Email Normalization**

All emails are normalized to lowercase automatically:

**Implementation:**
```python
def save(self, *args, **kwargs):
    self.email = self.email.lower()
    super().save(*args, **kwargs)

def clean(self):
    super().clean()
    self.email = self.email.lower()
```

**Benefit:** Prevents case-sensitivity issues (e.g., `John@Example.com` vs `john@example.com`)

### 7. **Model-Level Validation**

The `User` model includes:
- `USERNAME_FIELD = "email"` - Uses email as the unique username
- `clean()` method - Normalizes email to lowercase
- `save()` method - Normalizes email before persisting

## Database Schema

### users table structure
```
id                  | bigint         | PRIMARY KEY
password            | varchar        | (encrypted)
last_login          | timestamp      | (nullable)
is_superuser        | boolean        |
created_at          | timestamp      | (auto)
updated_at          | timestamp      | (auto)
email               | varchar        | UNIQUE NOT NULL
email_verified      | boolean        | default=False
first_name          | varchar        | (nullable)
last_name           | varchar        | (nullable)
phone_number        | varchar        | (nullable)
is_active           | boolean        | default=True
is_staff            | boolean        | default=False
locale              | varchar        | default='en-nz'
role                | varchar        | default='observer'
uuid                | uuid           | UNIQUE NOT NULL (NEW)
household_id        | bigint         | (FK, nullable)
```

## Verification Results

As of 2025-11-16 23:41:38:

```
Total Users:        34
Unique Emails:      34 ✓
Unique UUIDs:       34 ✓
Unique IDs:         34 ✓

✓ No duplicate emails detected
✓ No duplicate UUIDs detected
✓ No duplicate IDs detected
✓ All constraints in place
✓ All indexes created
```

## Usage Examples

### Creating a User with Rate Limiting

```python
from users.models import User
from django.http import HttpRequest
from django.core.exceptions import ValidationError

def register_user(request: HttpRequest, email: str, password: str):
    # Get client IP address
    ip_address = get_client_ip(request)
    
    # Check rate limit
    if User.check_creation_rate_limit(ip_address):
        raise ValidationError("Too many accounts created from this IP. Try again later.")
    
    # Create user
    try:
        user = User.objects.create_user(
            email=email,
            password=password,
        )
        # Increment rate limit counter
        User.increment_creation_rate_limit(ip_address)
        return user
    except IntegrityError:
        # Email already exists (caught at database level)
        raise ValidationError("This email is already registered.")
```

### Checking Email Verification

```python
def require_verified_email(user):
    if not user.is_email_verified_for_action():
        raise PermissionDenied("Please verify your email address first.")
```

### Using UUID for External APIs

```python
# In API serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['uuid', 'email', 'first_name', 'last_name']  # Use UUID, not ID

# API URL: /api/users/{uuid}/
# Instead of: /api/users/{id}/
```

## Security Benefits

1. **ID Enumeration Prevention**: Using UUID in public APIs prevents attackers from guessing user IDs
2. **Rate Limiting**: Prevents automated account creation attacks
3. **Email Uniqueness**: Database-level constraint prevents duplicate emails
4. **Email Verification**: Ensures users control the email accounts they register
5. **Audit Trail**: Created/updated timestamps for all users

## Future Enhancements

1. **Phone Number Uniqueness**: Consider making phone_number unique if required for recovery
2. **Account Deletion Policy**: Implement soft deletes with grace period before permanent deletion
3. **Duplicate Detection System**: Automated system to detect suspicious account patterns
4. **CAPTCHA Integration**: Add CAPTCHA to registration form for additional abuse prevention
5. **IP Whitelist/Blacklist**: Maintain lists of trusted/blocked IP addresses

## Related Files

- Model: `apps/users/models.py`
- Migration: `apps/users/migrations/0004_add_uuid_field.py`
- Manager: `apps/users/managers.py`
- Manager: `apps/users/enums.py`
- Serializers: `apps/users/serializers.py`
- Views: `apps/users/viewsets.py`

## Testing

To verify all measures are in place:

```bash
python check_user_uniqueness.py
```

This will display:
- All unique identifiers for a sample user
- Database constraints
- Active indexes
- Current duplicate detection status
- Rate limiting implementation
- Email verification status
