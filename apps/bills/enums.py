# apps/bills/enums.py

BILL_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("paid", "Paid"),
    ("overdue", "Overdue"),
    ("cancelled", "Cancelled"),
]

BILL_FREQUENCY_CHOICES = [
    ("weekly", "Weekly"),
    ("fortnightly", "Fortnightly"),
    ("monthly", "Monthly"),
    ("quarterly", "Quarterly"),
    ("yearly", "Yearly"),
    ("one_time", "One Time"),
]
