# apps/organisations/enums.py

ORGANISATION_TYPE_CHOICES = [
    ("corp", "Corporation"),
    ("npo", "Non-Profit Organisation"),
    ("edu", "Educational Institution"),
    ("gov", "Government Agency"),
    ("club", "Club/Community Group"),
    ("other", "Other"),
]

ORGANISATION_SUBSCRIPTION_CHOICES = [
    ("ww_starter", "Whānau Works Starter"),  # Basic tier
    ("ww_growth", "Whānau Works Growth"),  # Mid tier
    ("ww_enterprise", "Whānau Works Enterprise"),  # Full features
]

ORG_BUDGET_CYCLE_CHOICES = [
    ("m", "Monthly"),
    ("q", "Quarterly"),
    ("y", "Yearly"),
]

CURRENCY_CHOICES = [
    ("NZD", "New Zealand Dollar"),
    ("AUD", "Australian Dollar"),
    ("USD", "US Dollar"),
    ("GBP", "British Pound"),
    ("EUR", "Euro"),
]

ORG_PAYMENT_STATUS_CHOICES = [
    ("active", "Active"),
    ("trial", "Trial Period"),
    ("suspended", "Suspended"),
    ("cancelled", "Cancelled"),
]
