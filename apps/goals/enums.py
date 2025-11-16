# apps/goals/enums.py

GOAL_STATUS_CHOICES = [
    ("active", "Active"),
    ("completed", "Completed"),
    ("paused", "Paused"),
    ("cancelled", "Cancelled"),
]

GOAL_TYPE_CHOICES = [
    ("savings", "Savings Goal"),
    ("debt_payoff", "Debt Payoff"),
    ("purchase", "Purchase Goal"),
    ("emergency_fund", "Emergency Fund"),
    ("investment", "Investment Goal"),
    ("other", "Other"),
]
