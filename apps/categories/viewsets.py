from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Category
from .serializers import (
    CategorySerializer,
    CategoryCreateSerializer,
    CategoryUpdateSerializer,
)
from .permissions import IsCategoryHouseholdMember


class CategoryViewSet(viewsets.ModelViewSet):
    """
    Household-scoped Category CRUD.
    System categories are protected.
    Soft-delete enabled.
    """

    permission_classes = [permissions.IsAuthenticated, IsCategoryHouseholdMember]

    def get_queryset(self):
        user = self.request.user

        if user.is_staff:
            qs = Category.objects.all()
        else:
            qs = Category.objects.filter(household=user.household)

        # Optional filters
        category_type = self.request.query_params.get("category_type")
        if category_type:
            qs = qs.filter(category_type=category_type)

        active = self.request.query_params.get("active")
        if active in ["true", "false"]:
            qs = qs.filter(is_active=(active == "true"))

        deleted = self.request.query_params.get("deleted")
        if deleted in ["true", "false"]:
            qs = qs.filter(is_deleted=(deleted == "true"))

        return qs

    def get_serializer_class(self):
        if self.action == "create":
            return CategoryCreateSerializer
        if self.action in ["update", "partial_update"]:
            return CategoryUpdateSerializer
        return CategorySerializer

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete instead of hard delete.
        """
        category = self.get_object()

        if category.is_system:
            return Response(
                {"detail": "System categories cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category.is_deleted = True
        category.is_active = False
        category.save(update_fields=["is_deleted", "is_active", "updated_at"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="restore")
    def restore(self, request, pk=None):
        """
        Restore a soft-deleted category.
        """
        category = self.get_object()

        if category.is_system:
            return Response(
                {"detail": "System categories cannot be restored."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        category.is_deleted = False
        category.is_active = True
        category.save(update_fields=["is_deleted", "is_active", "updated_at"])

        serializer = CategorySerializer(category)
        return Response(serializer.data, status=status.HTTP_200_OK)
