from rest_framework import permissions


class IsRewardOwnerOrAdmin(permissions.BasePermission):
    """
    Users may only access their own rewards.
    Staff may access all.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False

        if request.user.is_staff:
            return True

        return obj.user_id == request.user.id
