"""
Integration tests for Reward ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from users.models import User
from rewards.models import Reward


@pytest.mark.django_db
class TestRewardViewSetList:
    """Test reward list endpoint."""

    def test_list_rewards_authenticated_user(self):
        """Users see their own rewards ordered by earned_on descending."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            first_name="Test",
        )
        Reward.objects.create(
            user=user,
            reward_type="milestone",
            title="First Budget Created",
            points=100,
            earned_on=timezone.now() - timedelta(days=1),
        )
        Reward.objects.create(
            user=user,
            reward_type="budget_saved",
            title="Saved $1000",
            points=500,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/rewards/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2
        # Should be ordered by earned_on descending (newest first)
        assert response.data[0]["title"] == "Saved $1000"

    def test_list_rewards_user_isolation(self):
        """Users only see their own rewards, not other users'."""
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
        )
        user2 = User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
        )

        Reward.objects.create(
            user=user1,
            reward_type="milestone",
            title="User 1 Reward",
            points=100,
            earned_on=timezone.now(),
        )
        Reward.objects.create(
            user=user2,
            reward_type="milestone",
            title="User 2 Reward",
            points=200,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/rewards/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["title"] == "User 1 Reward"

    def test_list_rewards_staff_sees_all(self):
        """Staff users see all rewards."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
        )
        user2 = User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
        )

        Reward.objects.create(
            user=user1,
            reward_type="milestone",
            title="R1",
            points=100,
            earned_on=timezone.now(),
        )
        Reward.objects.create(
            user=user2,
            reward_type="milestone",
            title="R2",
            points=200,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/rewards/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_list_rewards_unauthenticated(self):
        """Unauthenticated users cannot access rewards."""
        client = APIClient()
        response = client.get("/api/v1/rewards/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestRewardViewSetRetrieve:
    """Test reward retrieve endpoint."""

    def test_retrieve_own_reward(self):
        """User can retrieve their own reward."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        reward = Reward.objects.create(
            user=user,
            reward_type="milestone",
            title="Test Reward",
            description="Well done!",
            points=250,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/rewards/{reward.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Test Reward"
        assert response.data["points"] == 250

    def test_retrieve_other_user_reward(self):
        """User cannot retrieve another user's reward."""
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
        )
        user2 = User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
        )
        reward = Reward.objects.create(
            user=user2,
            reward_type="milestone",
            title="User 2 Reward",
            points=100,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get(f"/api/v1/rewards/{reward.id}/")

        # Returns 404 because queryset filtering happens before permission check
        # This is more secure (doesn't leak object existence)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_retrieve_any_reward_as_staff(self):
        """Staff can retrieve any reward."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        reward = Reward.objects.create(
            user=user,
            reward_type="milestone",
            title="User Reward",
            points=100,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/rewards/{reward.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "User Reward"


@pytest.mark.django_db
class TestRewardViewSetReadOnly:
    """Test that RewardViewSet is read-only."""

    def test_create_reward_not_allowed(self):
        """Creating rewards via ViewSet is not allowed."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/rewards/",
            {
                "reward_type": "milestone",
                "title": "New Reward",
                "points": 100,
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_reward_not_allowed(self):
        """Updating rewards via ViewSet is not allowed."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        reward = Reward.objects.create(
            user=user,
            reward_type="milestone",
            title="Original",
            points=100,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.put(
            f"/api/v1/rewards/{reward.id}/",
            {
                "title": "Updated",
                "points": 200,
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_reward_not_allowed(self):
        """Deleting rewards via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        reward = Reward.objects.create(
            user=admin_user,
            reward_type="milestone",
            title="Test",
            points=100,
            earned_on=timezone.now(),
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.delete(f"/api/v1/rewards/{reward.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
