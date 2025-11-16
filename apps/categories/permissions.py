from rest_framework import permissions


class IsCategoryHouseholdMember(permissions.BasePermission):
    """
    Prevents access to categories outside user's household.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True

        return obj.household_id == request.user.household_id
