"""
Tests for common test utilities.
"""

import pytest
from django.test import TestCase
from apps.common.test_utils import (
    BaseTestCase,
    BaseAPITestCase,
    create_test_user,
    create_test_household,
    get_model,
)


@pytest.mark.django_db
class TestGetModel(TestCase):
    """Test get_model utility function."""

    def test_get_user_model(self):
        """Can retrieve User model."""
        user_model = get_model("users", "User")
        self.assertIsNotNone(user_model)
        self.assertEqual(user_model.__name__, "User")

    def test_get_household_model(self):
        """Can retrieve Household model."""
        household_model = get_model("households", "Household")
        self.assertIsNotNone(household_model)
        self.assertEqual(household_model.__name__, "Household")


@pytest.mark.django_db
class TestBaseTestCase(TestCase):
    """Test BaseTestCase functionality."""

    def test_setup_creates_household(self):
        """setUp creates household instance."""
        test_case = BaseTestCase()
        test_case.setUp()

        self.assertIsNotNone(test_case.household)
        self.assertEqual(test_case.household.name, "Test Household")

    def test_setup_creates_user(self):
        """setUp creates user instance."""
        test_case = BaseTestCase()
        test_case.setUp()

        self.assertIsNotNone(test_case.user)
        self.assertEqual(test_case.user.email, "test@example.com")
        self.assertEqual(test_case.user.household, test_case.household)

    def test_teardown_cleans_up(self):
        """tearDown removes created instances."""
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        household_model = get_model("households", "Household")

        initial_user_count = user_model.objects.count()
        initial_household_count = household_model.objects.count()

        test_case = BaseTestCase()
        test_case.setUp()
        test_case.tearDown()

        self.assertEqual(user_model.objects.count(), initial_user_count)
        self.assertEqual(household_model.objects.count(), initial_household_count)


@pytest.mark.django_db
class TestBaseAPITestCase(TestCase):
    """Test BaseAPITestCase functionality."""

    def test_setup_creates_household(self):
        """setUp creates household instance."""
        test_case = BaseAPITestCase()
        test_case.setUp()

        self.assertIsNotNone(test_case.household)
        self.assertEqual(test_case.household.name, "API Test Household")

    def test_setup_creates_user(self):
        """setUp creates user instance."""
        test_case = BaseAPITestCase()
        test_case.setUp()

        self.assertIsNotNone(test_case.user)
        self.assertEqual(test_case.user.email, "api@example.com")

    def test_setup_creates_authenticated_client(self):
        """setUp creates authenticated API client."""
        test_case = BaseAPITestCase()
        test_case.setUp()

        self.assertIsNotNone(test_case.client)
        # Client should be authenticated
        self.assertTrue(hasattr(test_case.client, "force_authenticate"))

    def test_teardown_cleans_up(self):
        """tearDown removes created instances."""
        from django.contrib.auth import get_user_model

        user_model = get_user_model()
        household_model = get_model("households", "Household")

        initial_user_count = user_model.objects.count()
        initial_household_count = household_model.objects.count()

        test_case = BaseAPITestCase()
        test_case.setUp()
        test_case.tearDown()

        self.assertEqual(user_model.objects.count(), initial_user_count)
        self.assertEqual(household_model.objects.count(), initial_household_count)


@pytest.mark.django_db
class TestCreateTestUser(TestCase):
    """Test create_test_user factory function."""

    def test_creates_user_with_defaults(self):
        """Creates user with default values."""
        user = create_test_user()

        self.assertEqual(user.email, "user@test.com")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertIsNotNone(user.household)

    def test_creates_user_with_custom_email(self):
        """Creates user with custom email."""
        user = create_test_user(email="custom@test.com")

        self.assertEqual(user.email, "custom@test.com")

    def test_creates_user_with_provided_household(self):
        """Uses provided household."""
        household = create_test_household(name="Custom Household")
        user = create_test_user(household=household)

        self.assertEqual(user.household, household)
        self.assertEqual(user.household.name, "Custom Household")

    def test_creates_user_with_kwargs(self):
        """Creates user with additional kwargs."""
        user = create_test_user(first_name="John", last_name="Doe")

        self.assertEqual(user.first_name, "John")
        self.assertEqual(user.last_name, "Doe")

    def test_creates_household_when_none_provided(self):
        """Creates household automatically when not provided."""
        user = create_test_user(email="auto@test.com")

        self.assertIsNotNone(user.household)
        self.assertEqual(user.household.name, "Household for auto@test.com")


@pytest.mark.django_db
class TestCreateTestHousehold(TestCase):
    """Test create_test_household factory function."""

    def test_creates_household_with_defaults(self):
        """Creates household with default values."""
        household = create_test_household()

        self.assertEqual(household.name, "Test Household")
        self.assertEqual(household.household_type, "fam")
        self.assertEqual(household.budget_cycle, "m")

    def test_creates_household_with_custom_name(self):
        """Creates household with custom name."""
        household = create_test_household(name="Custom Family")

        self.assertEqual(household.name, "Custom Family")

    def test_creates_household_with_kwargs(self):
        """Creates household with additional kwargs."""
        household = create_test_household(
            name="School", household_type="sch", budget_cycle="w"
        )

        self.assertEqual(household.name, "School")
        self.assertEqual(household.household_type, "sch")
        self.assertEqual(household.budget_cycle, "w")
