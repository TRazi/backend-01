#!/usr/bin/env python
"""
Clear all users and related data from the database.
This will delete all users, households, organisations, and related data.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.users.models import User
from apps.households.models import Household, Membership
from apps.organisations.models import Organisation
from apps.accounts.models import Account
from apps.transactions.models import (
    Transaction,
    TransactionTag,
    TransactionAttachment,
    TransactionSplit,
)
from apps.categories.models import Category
from apps.budgets.models import Budget, BudgetItem
from apps.goals.models import Goal, GoalProgress
from apps.bills.models import Bill, BillAttachment
from apps.rewards.models import Reward


def clear_all_data():
    """Delete all users and related data."""
    print("=" * 80)
    print("⚠️  WARNING: This will delete ALL users and related data!")
    print("=" * 80)

    # Count existing data
    user_count = User.objects.count()
    household_count = Household.objects.count()
    org_count = Organisation.objects.count()
    account_count = Account.objects.count()
    transaction_count = Transaction.objects.count()
    category_count = Category.objects.count()
    budget_count = Budget.objects.count()
    goal_count = Goal.objects.count()
    bill_count = Bill.objects.count()
    reward_count = Reward.objects.count()

    print(f"\n📊 Current database state:")
    print(f"   Users: {user_count}")
    print(f"   Households: {household_count}")
    print(f"   Organisations: {org_count}")
    print(f"   Accounts: {account_count}")
    print(f"   Transactions: {transaction_count}")
    print(f"   Categories: {category_count}")
    print(f"   Budgets: {budget_count}")
    print(f"   Goals: {goal_count}")
    print(f"   Bills: {bill_count}")
    print(f"   Rewards: {reward_count}")

    print("\n🗑️  Deleting data in correct order (respecting foreign keys)...")

    # Delete in reverse order of dependencies
    deleted_counts = {}

    # Transaction-related (most dependent)
    deleted_counts["TransactionSplit"] = TransactionSplit.objects.all().delete()[0]
    deleted_counts["TransactionAttachment"] = (
        TransactionAttachment.objects.all().delete()[0]
    )
    deleted_counts["TransactionTag"] = TransactionTag.objects.all().delete()[0]
    deleted_counts["Transaction"] = Transaction.objects.all().delete()[0]

    # Other dependent models
    deleted_counts["GoalProgress"] = GoalProgress.objects.all().delete()[0]
    deleted_counts["Goal"] = Goal.objects.all().delete()[0]
    deleted_counts["BudgetItem"] = BudgetItem.objects.all().delete()[0]
    deleted_counts["Budget"] = Budget.objects.all().delete()[0]
    deleted_counts["BillAttachment"] = BillAttachment.objects.all().delete()[0]
    deleted_counts["Bill"] = Bill.objects.all().delete()[0]
    deleted_counts["Reward"] = Reward.objects.all().delete()[0]
    deleted_counts["Category"] = Category.objects.all().delete()[0]
    deleted_counts["Account"] = Account.objects.all().delete()[0]

    # Membership and organisations
    deleted_counts["Membership"] = Membership.objects.all().delete()[0]
    deleted_counts["Organisation"] = Organisation.objects.all().delete()[0]
    deleted_counts["Household"] = Household.objects.all().delete()[0]

    # Finally, users
    deleted_counts["User"] = User.objects.all().delete()[0]

    print("\n✅ Deletion complete!")
    print(f"\n📊 Deleted records:")
    for model, count in deleted_counts.items():
        if count > 0:
            print(f"   {model}: {count}")

    print("\n🎉 Database is now clean and ready for fresh data!")


if __name__ == "__main__":
    clear_all_data()
