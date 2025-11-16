"""
Common test utilities and base classes for KinWise test suite.

Provides:
- BaseTestCase: Standard Django test case with household/user setup
- BaseAPITestCase: REST framework test case with authentication
- Test data factories and helpers

Note: This module is imported by pytest during test collection.
Imports use Django's app registry to avoid import errors.
"""

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient


def get_model(app_label, model_name):
    """
    Get model class from app registry.

    Args:
        app_label: App label (e.g., 'users', 'households')
        model_name: Model class name (e.g., 'User', 'Household')

    Returns:
        Model class
    """
    from django.apps import apps

    return apps.get_model(app_label, model_name)


class BaseTestCase(TestCase):
    """
    Base test case with common setup for household and user.

    Attributes:
        household: Test household instance
        user: Test user instance belonging to household

    Example:
        class MyModelTest(BaseTestCase):
            def test_something(self):
                # self.household and self.user are available
                pass
    """

    def setUp(self):
        """Create test household and user."""
        from django.apps import apps

        household_model = get_model("households", "Household")
        user_model = get_model("users", "User")

        self.household = household_model.objects.create(
            name="Test Household",
            household_type="fam",
            budget_cycle="m",
        )
        self.user = user_model.objects.create_user(
            email="test@example.com",
            password="testpass123456",
            household=self.household,
            first_name="Test",
            last_name="User",
        )

    def tearDown(self):
        """Clean up test data."""
        from django.apps import apps

        user_model = get_model("users", "User")
        household_model = get_model("households", "Household")

        user_model.objects.all().delete()
        household_model.objects.all().delete()


class BaseAPITestCase(APITestCase):
    """
    Base API test case with authenticated client.

    Attributes:
        household: Test household instance
        user: Test user instance belonging to household
        client: Authenticated API client

    Example:
        class MyAPITest(BaseAPITestCase):
            def test_api_endpoint(self):
                response = self.client.get('/api/v1/transactions/')
                self.assertEqual(response.status_code, 200)
    """

    def setUp(self):
        """Create authenticated client with household and user."""
        from django.apps import apps

        household_model = get_model("households", "Household")
        user_model = get_model("users", "User")

        self.household = household_model.objects.create(
            name="API Test Household",
            household_type="fam",
            budget_cycle="m",
        )
        self.user = user_model.objects.create_user(
            email="api@example.com",
            password="testpass123456",
            household=self.household,
            first_name="API",
            last_name="User",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        """Clean up test data."""
        from django.apps import apps

        user_model = get_model("users", "User")
        household_model = get_model("households", "Household")

        self.client.force_authenticate(user=None)
        user_model.objects.all().delete()
        household_model.objects.all().delete()


def create_test_user(email="user@test.com", household=None, **kwargs):
    """
    Factory function to create test users.

    Args:
        email: User email address
        household: Household instance (created if None)
        **kwargs: Additional User model fields

    Returns:
        User instance
    """
    from django.apps import apps

    user_model = get_model("users", "User")
    household_model = get_model("households", "Household")

    if household is None:
        household = household_model.objects.create(name=f"Household for {email}")

    defaults = {
        "password": "testpass123456",
        "first_name": "Test",
        "last_name": "User",
    }
    defaults.update(kwargs)

    return user_model.objects.create_user(email=email, household=household, **defaults)


def create_test_household(name="Test Household", **kwargs):
    """
    Factory function to create test households.

    Args:
        name: Household name
        **kwargs: Additional Household model fields

    Returns:
        Household instance
    """
    from django.apps import apps

    household_model = get_model("households", "Household")

    defaults = {
        "household_type": "fam",
        "budget_cycle": "m",
    }
    defaults.update(kwargs)

    return household_model.objects.create(name=name, **defaults)
