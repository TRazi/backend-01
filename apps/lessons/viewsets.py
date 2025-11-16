from rest_framework import viewsets
from rest_framework import permissions

from .models import FinancialLesson
from .serializers import FinancialLessonSerializer
from .permissions import IsAuthenticatedReadOnly


class FinancialLessonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only lessons API.
    - Only published lessons
    - Optional filtering by age_group, difficulty, category
    - Ordered by display_order then title
    """

    serializer_class = FinancialLessonSerializer
    permission_classes = [IsAuthenticatedReadOnly]

    def get_queryset(self):
        qs = FinancialLesson.objects.filter(is_published=True)

        # Optional Filters
        age_group = self.request.query_params.get("age_group")
        if age_group:
            qs = qs.filter(age_group=age_group)

        difficulty = self.request.query_params.get("difficulty")
        if difficulty:
            qs = qs.filter(difficulty=difficulty)

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__iexact=category)

        return qs
