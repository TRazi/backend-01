"""
Tests for categories service functions.
"""

import pytest

from categories.models import Category
from categories.services import create_default_categories, category_soft_delete
from households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
def test_create_default_categories():
    """Test creating default categories for a household."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    categories = create_default_categories(household=household)

    # Should create multiple categories (parents + children)
    assert len(categories) > 0

    # Verify all created categories belong to the household
    for category in categories:
        assert category.household == household

    # Verify parent categories were created
    parent_categories = Category.objects.filter(
        household=household, parent__isnull=True
    )
    assert parent_categories.count() > 0


@pytest.mark.django_db
@pytest.mark.unit
def test_create_default_categories_creates_hierarchy():
    """Test that default categories creates proper parent-child hierarchy."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    create_default_categories(household=household)

    # Check that some categories have children
    categories_with_children = Category.objects.filter(
        household=household, parent__isnull=True
    )

    has_children = False
    for parent_category in categories_with_children:
        if parent_category.subcategories.exists():
            has_children = True
            break

    assert has_children, "No parent categories have children"


@pytest.mark.django_db
@pytest.mark.unit
def test_category_soft_delete():
    """Test soft deleting a category."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    category = Category.objects.create(
        name="Test Category",
        category_type="ex",
        household=household,
    )

    # Soft delete the category
    category_soft_delete(category=category)

    # Verify it's marked as deleted
    category.refresh_from_db()
    assert category.is_deleted is True
    assert category.is_active is False


@pytest.mark.django_db
@pytest.mark.unit
def test_category_soft_delete_preserves_data():
    """Test that soft delete preserves category data."""
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    category = Category.objects.create(
        name="Important Category",
        category_type="ex",
        household=household,
    )

    original_name = category.name
    category_soft_delete(category=category)

    # Verify data is preserved
    category.refresh_from_db()
    assert category.name == original_name
    assert category.household == household
