# apps/households/enums.py

HOUSEHOLD_TYPE_CHOICES = [
    ("fam", "Family"),
    ("couple", "Couple"),
    ("student", "Student Flat"),
    ("single", "Individual"),
    # Legacy/deprecated values for backwards compatibility
    ("cpl", "Couple"),
    ("stud", "Student Flat"),
    ("ind", "Individual"),
]

BUDGET_CYCLE_CHOICES = [
    ("d", "Daily"),
    ("w", "Weekly"),
    ("f", "Fortnightly"),
    ("m", "Monthly"),
    ("c", "Custom"),
]

MEMBERSHIP_TYPE_CHOICES = [
    ("sw", "Starter Whānau"),  # Basic free membership
    ("fw", "Future Whānau"),  # Paid membership with extra features
    ("mm", "Money Mates"),  # Group membership for friends
    ("wp", "Whānau Plus"),  # Enhanced family membership
    ("ww", "Whānau Works"),  # Membership for work-related groups
    ("if", "Individual Freemium"),  # Individual finance management
]

MEMBERSHIP_STATUS_CHOICES = [
    ("active", "Active"),
    ("inactive", "Inactive"),
    ("pending", "Pending"),
    ("cancelled", "Cancelled"),
    ("expired", "Expired"),
]

PAYMENT_STATUS_CHOICES = [
    ("paid", "Paid"),
    ("pending", "Pending"),
    ("overdue", "Overdue"),
    ("failed", "Failed"),
]
