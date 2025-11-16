from rest_framework import permissions


class IsBillHouseholdMember(permissions.BasePermission):
    """
    Only allow access to bills belonging to the request user's household.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        # Staff bypass
        if request.user.is_staff:
            return True

        return obj.household_id == request.user.household_id
