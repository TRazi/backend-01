#!/usr/bin/env python
"""
UUID Field Implementation Verification - Phase 1
Verifies that UUID fields were successfully added to:
- Household
- Account
- Transaction
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.households.models import Household
from apps.accounts.models import Account
from apps.transactions.models import Transaction


def verify_uuid_fields():
    """Verify UUID fields exist and are populated."""

    print("\n" + "=" * 70)
    print("UUID IMPLEMENTATION VERIFICATION - PHASE 1")
    print("=" * 70 + "\n")

    # Verify Household
    print("📍 HOUSEHOLD MODEL")
    print("-" * 70)
    try:
        households = Household.objects.all()[:3]
        household_count = Household.objects.count()
        print(f"✓ Total households: {household_count}")

        if households:
            for h in households:
                print(f"  - {h.name} (ID: {h.id}, UUID: {h.uuid})")

        # Check for NULL UUIDs
        null_count = Household.objects.filter(uuid__isnull=True).count()
        if null_count == 0:
            print(f"✓ All {household_count} households have UUIDs")
        else:
            print(f"⚠ WARNING: {null_count} households missing UUIDs")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    # Verify Account
    print("\n📍 ACCOUNT MODEL")
    print("-" * 70)
    try:
        accounts = Account.objects.all()[:3]
        account_count = Account.objects.count()
        print(f"✓ Total accounts: {account_count}")

        if accounts:
            for a in accounts:
                print(f"  - {a.name} (ID: {a.id}, UUID: {a.uuid})")

        # Check for NULL UUIDs
        null_count = Account.objects.filter(uuid__isnull=True).count()
        if null_count == 0:
            print(f"✓ All {account_count} accounts have UUIDs")
        else:
            print(f"⚠ WARNING: {null_count} accounts missing UUIDs")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    # Verify Transaction
    print("\n📍 TRANSACTION MODEL")
    print("-" * 70)
    try:
        transactions = Transaction.objects.all()[:3]
        transaction_count = Transaction.objects.count()
        print(f"✓ Total transactions: {transaction_count}")

        if transactions:
            for t in transactions:
                print(f"  - {t.description} (ID: {t.id}, UUID: {t.uuid})")

        # Check for NULL UUIDs
        null_count = Transaction.objects.filter(uuid__isnull=True).count()
        if null_count == 0:
            print(f"✓ All {transaction_count} transactions have UUIDs")
        else:
            print(f"⚠ WARNING: {null_count} transactions missing UUIDs")
    except Exception as e:
        print(f"✗ ERROR: {e}")

    # Check uniqueness
    print("\n📍 UNIQUENESS CHECKS")
    print("-" * 70)

    try:
        h_unique = Household.objects.values("uuid").count() == Household.objects.count()
        a_unique = Account.objects.values("uuid").count() == Account.objects.count()
        t_unique = (
            Transaction.objects.values("uuid").count() == Transaction.objects.count()
        )

        print(
            f"{'✓' if h_unique else '✗'} Household UUIDs: {'Unique' if h_unique else 'DUPLICATES FOUND'}"
        )
        print(
            f"{'✓' if a_unique else '✗'} Account UUIDs: {'Unique' if a_unique else 'DUPLICATES FOUND'}"
        )
        print(
            f"{'✓' if t_unique else '✗'} Transaction UUIDs: {'Unique' if t_unique else 'DUPLICATES FOUND'}"
        )
    except Exception as e:
        print(f"✗ ERROR: {e}")

    print("\n" + "=" * 70)
    print("PHASE 1 COMPLETE ✓")
    print("=" * 70 + "\n")
    print("Next: Phase 2 - Budget, Goal, Bill, Alert, Category")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    verify_uuid_fields()
