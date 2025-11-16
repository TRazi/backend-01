# apps/alerts/enums.py

ALERT_TYPE_CHOICES = [
    ("budget_warning", "Budget Warning"),
    ("budget_exceeded", "Budget Exceeded"),
    ("bill_due", "Bill Due Soon"),
    ("bill_overdue", "Bill Overdue"),
    ("goal_milestone", "Goal Milestone Reached"),
    ("low_balance", "Low Account Balance"),
    ("unusual_spending", "Unusual Spending Detected"),
    ("recurring_transaction", "Recurring Transaction Reminder"),
    ("custom", "Custom Alert"),
]

ALERT_PRIORITY_CHOICES = [
    ("low", "Low"),
    ("medium", "Medium"),
    ("high", "High"),
    ("urgent", "Urgent"),
]

ALERT_STATUS_CHOICES = [
    ("active", "Active"),
    ("dismissed", "Dismissed"),
    ("resolved", "Resolved"),
]
