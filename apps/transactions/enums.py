# apps/transactions/enums.py

TRANSACTION_TYPE_CHOICES = [
    ("income", "Income"),
    ("expense", "Expense"),
    ("transfer", "Transfer"),
]

TRANSACTION_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
]

TRANSACTION_SOURCE_CHOICES = [
    ("manual", "Manual Entry"),
    ("voice", "Voice Entry"),
    ("receipt", "Receipt OCR"),
    ("bank_import", "Bank Import"),
]
