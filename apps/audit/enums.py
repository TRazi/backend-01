"""
Enums for audit logging.
"""

# Audit action types
ACTION_CHOICES = [
    # Authentication
    ("LOGIN", "User Login"),
    ("LOGOUT", "User Logout"),
    ("LOGIN_FAILED", "Failed Login Attempt"),
    ("PASSWORD_CHANGE", "Password Changed"),
    ("MFA_ENABLED", "MFA Enabled"),
    ("MFA_DISABLED", "MFA Disabled"),
    # CRUD operations
    ("CREATE", "Create"),
    ("UPDATE", "Update"),
    ("DELETE", "Delete"),
    ("VIEW", "View"),
    # Data operations
    ("EXPORT", "Data Export"),
    ("IMPORT", "Data Import"),
    ("BULK_DELETE", "Bulk Delete"),
    # Permission changes
    ("PERMISSION_GRANT", "Permission Granted"),
    ("PERMISSION_REVOKE", "Permission Revoked"),
    ("ROLE_CHANGE", "Role Changed"),
    # System events
    ("RATE_LIMIT_EXCEEDED", "Rate Limit Exceeded"),
    ("ACCOUNT_LOCKED", "Account Locked"),
    ("ACCOUNT_UNLOCKED", "Account Unlocked"),
    ("EMAIL_VERIFIED", "Email Verified"),
    ("OTP_REQUESTED", "OTP Requested"),
]

# Data export types
EXPORT_TYPE_CHOICES = [
    ("household_backup", "Household Full Backup"),
    ("transaction_export", "Transaction Export"),
    ("budget_report", "Budget Report"),
    ("spending_report", "Spending Report"),
    ("user_data_export", "User Personal Data Export (GDPR)"),
]
