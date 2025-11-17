# apps/reports/services.py
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Sum
from django.utils import timezone

from apps.households.models import Household, Membership
from apps.transactions.models import Transaction
from apps.budgets.models import Budget
from apps.goals.models import Goal
from apps.accounts.models import Account
from apps.categories.models import Category
from apps.audit.services import log_action
from apps.users.models import User


class ReportAccessError(ValueError):
    pass


def _get_household_for_user(*, user: User, household_id: int) -> Household:
    try:
        household = Household.objects.get(id=household_id)
    except Household.DoesNotExist:
        raise ReportAccessError("Household not found")

    is_member = Membership.objects.filter(
        user=user,
        household=household,
        ended_at__isnull=True,
    ).exists()

    if not is_member:
        raise ReportAccessError("You must be a member of this household")

    return household


def generate_spending_report(
    *,
    user: User,
    household_id: int,
    from_date: datetime,
    to_date: datetime,
    category_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Household-level spending report (v2).

    - Filters by account__household
    - Uses Transaction.date
    - Aggregates expenses (transaction_type='expense', status='completed')
    """
    household = _get_household_for_user(user=user, household_id=household_id)

    qs = Transaction.objects.filter(
        account__household=household,
        date__gte=from_date,
        date__lte=to_date,
        status="completed",
        transaction_type="expense",
    ).select_related("category")

    if category_id:
        qs = qs.filter(category_id=category_id)

    total_spent = qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    # amount is negative for expenses, normalise to positive
    total_spent = abs(total_spent)

    by_category: List[Dict[str, Any]] = []
    category_rows = (
        qs.values("category_id", "category__name")
        .annotate(total=Sum("amount"))
        .order_by("category__name")
    )

    for row in category_rows:
        cat_total = row["total"] or Decimal("0.00")
        cat_total = abs(cat_total)
        category_name = row["category__name"] or "Uncategorised"

        percent_of_total = (
            float(cat_total / total_spent * Decimal("100")) if total_spent > 0 else 0.0
        )

        by_category.append(
            {
                "category_id": row["category_id"],
                "category_name": category_name,
                "spent": str(cat_total),
                "percentage_of_total": percent_of_total,
            }
        )

    result = {
        "metadata": {
            "generated_at": timezone.now().isoformat(),
            "household_id": household.id,
            "household_name": household.name,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "filter_category_id": category_id,
        },
        "summary": {
            "total_spent": str(total_spent),
            "category_count": len(by_category),
        },
        "by_category": by_category,
    }

    log_action(
        user=user,
        household=household,
        action_type="VIEW",
        action_description=f"Generated spending report for {household.name}",
        metadata={
            "report_type": "spending",
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "category_id": category_id,
            "total_spent": str(total_spent),
        },
    )

    return result


def export_household_snapshot(*, user: User, household_id: int) -> Dict[str, Any]:
    """
    Lightweight 'backup' export for a household.
    This is the v2 equivalent of HouseholdExportApi: good for
    CSV/JSON exports or basic offline backup.
    """
    household = _get_household_for_user(user=user, household_id=household_id)

    accounts = Account.objects.filter(household=household)
    budgets = Budget.objects.filter(household=household)
    goals = Goal.objects.filter(household=household)
    categories = Category.objects.filter(household=household, is_deleted=False)

    result = {
        "metadata": {
            "exported_at": timezone.now().isoformat(),
            "household_id": household.id,
            "household_name": household.name,
        },
        "accounts": [
            {
                "id": a.id,
                "name": getattr(a, "name", None),
                "account_type": getattr(a, "account_type", None),
                "balance": str(getattr(a, "balance", 0)),
                "institution_name": getattr(a, "institution_name", None),
                "last4": getattr(a, "last4", None),
            }
            for a in accounts
        ],
        "budgets": [
            {
                "id": b.id,
                "name": b.name,
                "total_amount": str(b.total_amount),
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None,
                "status": b.status,
            }
            for b in budgets
        ],
        "goals": [
            {
                "id": g.id,
                "name": g.name,
                "target_amount": str(g.target_amount),
                "current_amount": str(g.current_amount),
                "due_date": g.due_date.isoformat() if g.due_date else None,
                "status": g.status,
            }
            for g in goals
        ],
        "categories": [
            {
                "id": c.id,
                "name": c.name,
                "category_type": c.category_type,
                "parent": c.parent_id,
                "is_system": c.is_system,
                "is_active": c.is_active,
            }
            for c in categories
        ],
    }

    log_action(
        user=user,
        household=household,
        action_type="EXPORT",
        action_description=f"Exported household snapshot for {household.name}",
        metadata={
            "export_type": "household_snapshot",
            "accounts": accounts.count(),
            "budgets": budgets.count(),
            "goals": goals.count(),
            "categories": categories.count(),
        },
    )

    return result
