"""
Custom permission classes for role-based access control
Enforces KinWise staff roles (Viewer, Editor, Manager)
"""

from rest_framework import permissions


class IsKinWiseViewer(permissions.BasePermission):
    """Only allow KinWise Viewer role or higher"""
    message = "You don't have permission to view this resource."
    
    def has_permission(self, request, view):
        return request.user and (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=[
                "KinWise Viewer",
                "KinWise Editor", 
                "KinWise Manager"
            ]).exists()
        )


class IsKinWiseEditor(permissions.BasePermission):
    """Only allow KinWise Editor role or higher (no delete)"""
    message = "You don't have permission to edit this resource."
    
    def has_permission(self, request, view):
        # GET, HEAD, OPTIONS are allowed for viewers too
        if request.method in permissions.SAFE_METHODS:
            return request.user and (
                request.user.is_superuser or 
                request.user.groups.filter(name__in=[
                    "KinWise Viewer",
                    "KinWise Editor", 
                    "KinWise Manager"
                ]).exists()
            )
        
        # POST, PUT, PATCH require Editor role or higher
        return request.user and (
            request.user.is_superuser or 
            request.user.groups.filter(name__in=[
                "KinWise Editor", 
                "KinWise Manager"
            ]).exists()
        )


class IsKinWiseManager(permissions.BasePermission):
    """Only allow KinWise Manager role or higher (full CRUD)"""
    message = "You don't have permission to perform this action."
    
    def has_permission(self, request, view):
        # GET, HEAD, OPTIONS allowed for viewers
        if request.method in permissions.SAFE_METHODS:
            return request.user and (
                request.user.is_superuser or 
                request.user.groups.filter(name__in=[
                    "KinWise Viewer",
                    "KinWise Editor", 
                    "KinWise Manager"
                ]).exists()
            )
        
        # DELETE requires Manager role or higher
        return request.user and (
            request.user.is_superuser or 
            request.user.groups.filter(name="KinWise Manager").exists()
        )


class IsKinWiseSuperAdmin(permissions.BasePermission):
    """Only allow super admins (you only)"""
    message = "Only KinWise super admins can perform this action."
    
    def has_permission(self, request, view):
        return request.user and request.user.is_superuser
