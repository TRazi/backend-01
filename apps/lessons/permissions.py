from rest_framework import permissions


class IsAuthenticatedReadOnly(permissions.BasePermission):
    """
    Lessons are readable by any authenticated user.
    No writes allowed.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return request.user and request.user.is_authenticated
