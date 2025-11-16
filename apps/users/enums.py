# apps/users/enums.py

ROLE_CHOICES = [
    ("admin", "Admin"),
    ("parent", "Parent"),
    ("teen", "Teen"),
    ("child", "Child"),
    ("flatmate", "Flatmate"),
    ("observer", "Observer"),
]

# Add locale choices based on Django's supported languages
LOCALE_CHOICES = [
    ("en", "English"),
    ("en-nz", "English (New Zealand)"),
    ("en-au", "English (Australia)"),
    ("en-gb", "English (UK)"),
    ("en-us", "English (US)"),  # We'll add this to Django settings
]
