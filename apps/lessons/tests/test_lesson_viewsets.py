"""
Integration tests for FinancialLesson ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status

from users.models import User
from lessons.models import FinancialLesson


@pytest.mark.django_db
class TestFinancialLessonViewSetList:
    """Test lesson list endpoint."""

    def test_list_published_lessons_authenticated(self):
        """Authenticated users see only published lessons."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        FinancialLesson.objects.create(
            title="Published Lesson",
            content="Content here",
            is_published=True,
            age_group="teen",
        )
        FinancialLesson.objects.create(
            title="Unpublished Lesson",
            content="Hidden content",
            is_published=False,
            age_group="teen",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/lessons/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Published Lesson"

    def test_list_lessons_unauthenticated(self):
        """Unauthenticated users cannot access lessons (requires authentication)."""
        FinancialLesson.objects.create(
            title="Public Lesson",
            content="Content",
            is_published=True,
        )

        client = APIClient()
        response = client.get("/api/v1/lessons/")

        # ViewSet requires authentication
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_filter_by_age_group(self):
        """Users can filter lessons by age group."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        FinancialLesson.objects.create(
            title="Kids Lesson",
            content="Content",
            is_published=True,
            age_group="child",
        )
        FinancialLesson.objects.create(
            title="Teens Lesson",
            content="Content",
            is_published=True,
            age_group="teen",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/lessons/?age_group=teen")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Teens Lesson"

    def test_filter_by_difficulty(self):
        """Users can filter lessons by difficulty level."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        FinancialLesson.objects.create(
            title="Beginner Lesson",
            content="Content",
            is_published=True,
            difficulty="beginner",
        )
        FinancialLesson.objects.create(
            title="Advanced Lesson",
            content="Content",
            is_published=True,
            difficulty="advanced",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/lessons/?difficulty=beginner")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Beginner Lesson"

    def test_filter_by_category(self):
        """Users can filter lessons by category."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        FinancialLesson.objects.create(
            title="Budgeting Lesson",
            content="Content",
            is_published=True,
            category="Budgeting",
        )
        FinancialLesson.objects.create(
            title="Saving Lesson",
            content="Content",
            is_published=True,
            category="Saving",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/lessons/?category=budgeting")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "Budgeting Lesson"


@pytest.mark.django_db
class TestFinancialLessonViewSetRetrieve:
    """Test lesson retrieve endpoint."""

    def test_retrieve_published_lesson(self):
        """Users can retrieve published lessons."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        lesson = FinancialLesson.objects.create(
            title="Test Lesson",
            content="Detailed content here",
            is_published=True,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/lessons/{lesson.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Test Lesson"

    def test_retrieve_unpublished_lesson(self):
        """Users cannot retrieve unpublished lessons."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        lesson = FinancialLesson.objects.create(
            title="Hidden Lesson",
            content="Secret content",
            is_published=False,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/lessons/{lesson.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestFinancialLessonViewSetReadOnly:
    """Test that FinancialLessonViewSet is read-only."""

    def test_create_lesson_not_allowed(self):
        """Creating lessons via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post(
            "/api/v1/lessons/",
            {
                "title": "New Lesson",
                "content": "Content",
                "is_published": True,
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_lesson_not_allowed(self):
        """Updating lessons via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        lesson = FinancialLesson.objects.create(
            title="Original",
            content="Content",
            is_published=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.put(
            f"/api/v1/lessons/{lesson.id}/",
            {
                "title": "Updated",
                "content": "New content",
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_lesson_not_allowed(self):
        """Deleting lessons via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        lesson = FinancialLesson.objects.create(
            title="Test",
            content="Content",
            is_published=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.delete(f"/api/v1/lessons/{lesson.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
