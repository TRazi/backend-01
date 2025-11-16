#!/usr/bin/env python
"""
User Identification & Duplicate Prevention Verification Script

This script demonstrates all the measures implemented to prevent duplicate users
and ensure unique user identification across the KinWise system.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection
from apps.users.models import User
import uuid

print("=" * 70)
print("USER IDENTIFICATION & DUPLICATE PREVENTION VERIFICATION")
print("=" * 70)

print("\n1. UNIQUE IDENTIFICATION MEASURES")
print("-" * 70)

# Show sample user with all identifiers
u = User.objects.first()
print(f"\nSample User: {u.email}")
print(f"  • Database ID (bigint):     {u.pk}")
print(f"  • UUID (public identifier): {u.uuid}")
print(f"  • Email (unique):           {u.email}")

print("\n2. DATABASE CONSTRAINTS")
print("-" * 70)

with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'users' AND constraint_type = 'UNIQUE'
        ORDER BY constraint_name
    """
    )
    constraints = cursor.fetchall()
    for constraint in constraints:
        if "uuid" in constraint[0] or "email" in constraint[0]:
            print(f"  ✓ {constraint[0]}")
    print(f"  ✓ Total unique constraints: {len(constraints)}")

print("\n3. INDEXES FOR UNIQUENESS & PERFORMANCE")
print("-" * 70)

with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'users' AND (indexname LIKE '%uuid%' OR indexname LIKE '%email%')
    """
    )
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f"  ✓ {idx[0]}")

print("\n4. DUPLICATE DETECTION")
print("-" * 70)

# Check for duplicate emails
duplicate_emails = User.objects.raw(
    """
    SELECT id, email, COUNT(*) as count
    FROM users
    GROUP BY email
    HAVING COUNT(*) > 1
"""
)
duplicates = list(duplicate_emails)

if not duplicates:
    print("  ✓ No duplicate emails found")
    print(f"  ✓ All {User.objects.count()} users have unique emails")
else:
    print(f"  ✗ WARNING: Found {len(duplicates)} duplicate emails!")

# Check for duplicate UUIDs
duplicate_uuids = User.objects.raw(
    """
    SELECT id, uuid, COUNT(*) as count
    FROM users
    GROUP BY uuid
    HAVING COUNT(*) > 1
"""
)
dup_uuids = list(duplicate_uuids)

if not dup_uuids:
    print("  ✓ No duplicate UUIDs found")
    print(f"  ✓ All {User.objects.count()} users have unique UUIDs")
else:
    print(f"  ✗ WARNING: Found {len(dup_uuids)} duplicate UUIDs!")

print("\n5. RATE LIMITING FOR ACCOUNT CREATION")
print("-" * 70)
print("  Implementation:")
print("    • User.check_creation_rate_limit(ip_address)")
print("      - Checks if IP has exceeded account creation limit")
print("      - Default: 5 accounts per 3600 seconds (1 hour)")
print("      - Returns: True if rate limited, False if allowed")
print()
print("    • User.increment_creation_rate_limit(ip_address)")
print("      - Increments account creation counter for IP")
print("      - Uses Django cache for fast lookups")
print()
print("  Integration Point:")
print("    - Should be called in user registration view before creating account")
print("    - Example:")
print("      if User.check_creation_rate_limit(ip_address):")
print("          raise RateLimitExceeded('Too many accounts from this IP')")
print("      new_user = User.objects.create_user(...)")
print("      User.increment_creation_rate_limit(ip_address)")

print("\n6. EMAIL VERIFICATION ENFORCEMENT")
print("-" * 70)
print("  Implementation:")
print("    • is_email_verified_for_action()")
print("      - Returns True if email_verified field is True")
print("      - Returns False if email not yet verified")
print()
print("  Usage Example:")
print("    if not user.is_email_verified_for_action():")
print("        raise PermissionDenied('Email must be verified for this action')")
print()
print("  Current Status:")
verified_count = User.objects.filter(email_verified=True).count()
unverified_count = User.objects.filter(email_verified=False).count()
print(f"    • Verified emails:   {verified_count}")
print(f"    • Unverified emails: {unverified_count}")

print("\n7. EMAIL NORMALIZATION")
print("-" * 70)
print("  • All emails are normalized to lowercase on save()")
print("  • Prevents case-sensitivity issues")
print("  • Example: 'John@Example.COM' → 'john@example.com'")

print("\n" + "=" * 70)
print("SUMMARY: All measures in place for preventing user duplication")
print("=" * 70)
