from rest_framework import permissions


class IsGoalHouseholdMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True

        return obj.household_id == request.user.household_id


class IsGoalProgressHouseholdMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        goal = obj.goal
        return goal.household_id == request.user.household_id or request.user.is_staff
