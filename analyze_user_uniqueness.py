#!/usr/bin/env python
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, models
from apps.users.models import User

print("User Identification & Uniqueness Analysis")
print("=" * 60)

# Check sample user
u = User.objects.first()
if u:
    print("\nSample User Data:")
    print(f"  Primary Key (ID): {u.pk} (type: {type(u.pk).__name__})")
    print(f"  Email: {u.email}")
    print(f"  Has Django ID field: {hasattr(u, 'id')}")

# Check database schema
print("\n\nDatabase Schema (users table):")
print("-" * 60)
with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = 'users' AND table_schema = 'public'
        ORDER BY ordinal_position
        LIMIT 15
    """
    )
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")

# Check uniqueness constraints
print("\n\nUniqueness Constraints:")
print("-" * 60)
with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT constraint_name, column_name
        FROM information_schema.constraint_column_usage
        WHERE table_name = 'users'
    """
    )
    try:
        constraints = cursor.fetchall()
        if constraints:
            for constraint in constraints:
                print(f"  {constraint[0]}: {constraint[1]}")
        else:
            print("  (checking constraints differently...)")
    except Exception as e:
        print(f"  Error: {e}")

# Check indexes
print("\n\nIndexes on users table:")
print("-" * 60)
with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'users'
    """
    )
    indexes = cursor.fetchall()
    for idx in indexes:
        print(f"  {idx[0]}: {idx[1]}")

# Check duplicate detection
print("\n\nDuplicate Detection Analysis:")
print("-" * 60)
duplicate_emails = (
    User.objects.values("email").annotate(count=models.Count("id")).filter(count__gt=1)
)

if duplicate_emails.exists():
    print("  WARNING: Found duplicate emails!")
    for dup in duplicate_emails:
        print(f"    {dup['email']}: {dup['count']} records")
else:
    print("  ✓ No duplicate emails found")
    print(f"  ✓ All {User.objects.count()} users have unique emails")

print("\n" + "=" * 60)
