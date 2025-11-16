from rest_framework import permissions


class IsAuditAdmin(permissions.BasePermission):
    """
    Only staff can view audit logs.
    No access for end-users.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_authenticated and request.user.is_staff
