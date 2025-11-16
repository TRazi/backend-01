from rest_framework import permissions


class IsAccountHouseholdMember(permissions.BasePermission):
    """
    Ensures access to accounts only within user's household.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True

        return obj.household_id == request.user.household_id
