from rest_framework import permissions


class IsAlertHouseholdMember(permissions.BasePermission):
    """
    Ensures a user can only access alerts that belong to their household.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Staff can see everything
        if request.user.is_staff:
            return True

        # Household-scoped access
        return obj.household_id == request.user.household_id
