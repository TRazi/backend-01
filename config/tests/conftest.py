# tests/conftest.py
import pytest
from rest_framework.test import APIClient

from users.models import User
from households.models import Household, Membership


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="user@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(
        email="other@example.com",
        password="testpass123",
    )


@pytest.fixture
def household():
    return Household.objects.create(name="Test Household")


@pytest.fixture
def membership(user, household):
    user.household = household
    user.save()
    return Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )


@pytest.fixture
def auth_client(user, membership):
    client = APIClient()
    client.force_authenticate(user=user)
    return client
