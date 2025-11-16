# Root conftest.py for Django pytest configuration
import os
import sys
import django
from pathlib import Path

# Add apps directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "apps"))

# Configure Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

# Setup Django
django.setup()

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        email="user@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def other_user(db):
    """Create another test user."""
    return User.objects.create_user(
        email="other@example.com",
        password="testpass123",
    )


@pytest.fixture
def household(db):
    """Create a test household."""
    from households.models import Household
    return Household.objects.create(name="Test Household")


@pytest.fixture
def membership(user, household, db):
    """Create a membership linking user to household."""
    from households.models import Membership
    user.household = household
    user.save()
    return Membership.objects.create(
        user=user,
        household=household,
        role="admin",
    )


@pytest.fixture
def auth_client(user, membership):
    """Create an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def api_client():
    """Create an unauthenticated API client."""
    return APIClient()
