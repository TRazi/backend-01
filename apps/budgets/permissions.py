from rest_framework import permissions


class IsBudgetHouseholdMember(permissions.BasePermission):
    """
    Ensures user only accesses budgets in their own household.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True

        return obj.household_id == request.user.household_id


class IsBudgetItemHouseholdMember(permissions.BasePermission):
    """
    Ensures user only accesses budget items for their household.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True

        return obj.budget.household_id == request.user.household_id
