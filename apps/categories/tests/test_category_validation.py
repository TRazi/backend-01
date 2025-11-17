"""Additional tests for Category model validation to reach 85% coverage."""

import pytest
from django.core.exceptions import ValidationError

from apps.categories.models import Category
from apps.households.models import Household


@pytest.mark.django_db
@pytest.mark.unit
class TestCategoryValidationEdgeCases:
    """Test edge cases for Category model clean() validation."""

    def test_clean_validates_self_referencing_parent(self):
        """Test clean raises error when category is its own parent."""
        household = Household.objects.create(name="Test Household")
        category = Category.objects.create(
            household=household, name="Self Reference", category_type="expense"
        )

        # Try to set itself as parent
        category.parent = category

        with pytest.raises(ValidationError, match="cannot be its own parent"):
            category.clean()

    def test_clean_validates_circular_parent_relationship(self):
        """Test clean raises error for circular parent relationships (A -> B -> A)."""
        household = Household.objects.create(name="Test Household")

        # Create category A
        cat_a = Category.objects.create(
            household=household, name="Category A", category_type="expense"
        )

        # Create category B with A as parent
        cat_b = Category.objects.create(
            household=household,
            name="Category B",
            category_type="expense",
            parent=cat_a,
        )

        # Try to set B as A's parent (creating a circle)
        cat_a.parent = cat_b

        with pytest.raises(
            ValidationError, match="Circular parent relationship detected"
        ):
            cat_a.clean()

    def test_clean_validates_parent_same_household(self):
        """Test clean raises error when parent belongs to different household."""
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        parent_category = Category.objects.create(
            household=household1, name="Parent Category", category_type="expense"
        )

        child_category = Category(
            household=household2,  # Different household
            name="Child Category",
            category_type="expense",
            parent=parent_category,
        )

        with pytest.raises(
            ValidationError, match="Parent category must belong to same household"
        ):
            child_category.clean()

    def test_clean_validates_duplicate_name_in_household(self):
        """Test clean raises error for duplicate category names in same household."""
        household = Household.objects.create(name="Test Household")

        # Create first category
        Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )

        # Try to create another with same name (case-insensitive)
        duplicate_category = Category(
            household=household, name="groceries", category_type="expense"
        )

        with pytest.raises(
            ValidationError,
            match="Category 'groceries' already exists in this household",
        ):
            duplicate_category.clean()

    def test_clean_allows_duplicate_name_if_deleted(self):
        """Test clean allows duplicate names if existing category is deleted."""
        household = Household.objects.create(name="Test Household")

        # Create and soft-delete first category
        deleted_cat = Category.objects.create(
            household=household, name="Groceries", category_type="expense"
        )
        deleted_cat.is_deleted = True
        deleted_cat.save()

        # Should allow creating another with same name
        new_category = Category(
            household=household, name="Groceries", category_type="expense"
        )

        # Should not raise ValidationError
        new_category.clean()  # Should pass

    def test_clean_allows_same_name_different_household(self):
        """Test clean allows same category name in different households."""
        household1 = Household.objects.create(name="Household 1")
        household2 = Household.objects.create(name="Household 2")

        # Create category in household1
        Category.objects.create(
            household=household1, name="Groceries", category_type="expense"
        )

        # Should allow creating same name in household2
        category2 = Category(
            household=household2, name="Groceries", category_type="expense"
        )

        # Should not raise ValidationError
        category2.clean()  # Should pass
