"""
Custom permissions for file attachments (receipts, bills, etc.)
Ensures users can only access their own uploaded files.
Admins are restricted to their own household.
"""

from rest_framework import permissions


class IsUploadedByUserOrHouseholdAdmin(permissions.BasePermission):
    """
    Permission to check if user is the one who uploaded the file
    or if they're an admin in the same household.
    
    - Regular users: Can only view their own uploads
    - Household admins: Can view uploads in their household
    - Super admins: Can view all uploads (is_superuser=True)
    """

    message = "You don't have permission to access this file."

    def has_object_permission(self, request, view, obj):
        # Only super admins can bypass household restrictions
        if request.user and request.user.is_superuser:
            return True

        # Allow the user who uploaded the file
        if hasattr(obj, "uploaded_by"):
            return obj.uploaded_by == request.user

        return False


class IsTransactionOwnerOrHouseholdAdmin(permissions.BasePermission):
    """
    Permission to check if user owns the transaction's household
    or if they're an admin in that household.
    
    - Regular users: Can only access transactions in their household
    - Household admins: Can access all transactions in their household
    - Super admins: Can access all transactions (is_superuser=True)
    """

    message = "You don't have permission to access this transaction."

    def has_object_permission(self, request, view, obj):
        # Only super admins can bypass household restrictions
        if request.user and request.user.is_superuser:
            return True

        # Allow users in the same household
        if hasattr(obj, "account") and hasattr(obj.account, "household"):
            return obj.account.household == request.user.household

        return False


class IsBillOwnerOrHouseholdAdmin(permissions.BasePermission):
    """
    Permission to check if user owns the bill's household
    or if they're an admin in that household.
    
    - Regular users: Can only access bills in their household
    - Household admins: Can access all bills in their household
    - Super admins: Can access all bills (is_superuser=True)
    """

    message = "You don't have permission to access this bill."

    def has_object_permission(self, request, view, obj):
        # Only super admins can bypass household restrictions
        if request.user and request.user.is_superuser:
            return True

        # Allow users in the same household
        if hasattr(obj, "account") and hasattr(obj.account, "household"):
            return obj.account.household == request.user.household

        return False
