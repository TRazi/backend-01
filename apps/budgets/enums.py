# apps/budgets/enums.py

BUDGET_STATUS_CHOICES = [
    ("active", "Active"),
    ("completed", "Completed"),
    ("exceeded", "Exceeded"),
    ("cancelled", "Cancelled"),
]

BUDGET_PERIOD_CHOICES = [
    ("weekly", "Weekly"),
    ("fortnightly", "Fortnightly"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("yearly", "Yearly"),
    ("custom", "Custom"),
]
