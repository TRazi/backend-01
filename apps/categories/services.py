# apps/categories/services.py
from typing import List
from django.db import transaction

from categories.models import Category
from households.models import Household


DEFAULT_CATEGORIES = [
    # Income categories
    {
        "name": "Income",
        "category_type": "income",
        "icon": "💰",
        "color": "#10B981",
        "children": [
            {"name": "Salary", "icon": "💼"},
            {"name": "Freelance", "icon": "💻"},
            {"name": "Investment Income", "icon": "📈"},
            {"name": "Other Income", "icon": "💵"},
        ],
    },
    # Expense categories
    {
        "name": "Housing",
        "category_type": "expense",
        "icon": "🏠",
        "color": "#3B82F6",
        "children": [
            {"name": "Rent/Mortgage", "icon": "🏘️"},
            {"name": "Utilities", "icon": "💡"},
            {"name": "Insurance", "icon": "🛡️"},
            {"name": "Maintenance", "icon": "🔧"},
        ],
    },
    {
        "name": "Food & Dining",
        "category_type": "expense",
        "icon": "🍽️",
        "color": "#F59E0B",
        "children": [
            {"name": "Groceries", "icon": "🛒"},
            {"name": "Restaurants", "icon": "🍔"},
            {"name": "Coffee & Snacks", "icon": "☕"},
        ],
    },
    {
        "name": "Transportation",
        "category_type": "expense",
        "icon": "🚗",
        "color": "#8B5CF6",
        "children": [
            {"name": "Fuel", "icon": "⛽"},
            {"name": "Public Transport", "icon": "🚌"},
            {"name": "Vehicle Maintenance", "icon": "🔧"},
            {"name": "Parking", "icon": "🅿️"},
        ],
    },
    {
        "name": "Entertainment",
        "category_type": "expense",
        "icon": "🎭",
        "color": "#EC4899",
        "children": [
            {"name": "Streaming Services", "icon": "📺"},
            {"name": "Movies & Events", "icon": "🎬"},
            {"name": "Hobbies", "icon": "🎨"},
        ],
    },
    {
        "name": "Shopping",
        "category_type": "expense",
        "icon": "🛍️",
        "color": "#EF4444",
        "children": [
            {"name": "Clothing", "icon": "👕"},
            {"name": "Electronics", "icon": "📱"},
            {"name": "Home & Garden", "icon": "🏡"},
        ],
    },
    {
        "name": "Health & Wellness",
        "category_type": "expense",
        "icon": "🏥",
        "color": "#14B8A6",
        "children": [
            {"name": "Medical", "icon": "💊"},
            {"name": "Fitness", "icon": "💪"},
            {"name": "Personal Care", "icon": "💆"},
        ],
    },
    {
        "name": "Education",
        "category_type": "expense",
        "icon": "📚",
        "color": "#6366F1",
        "children": [
            {"name": "Tuition", "icon": "🎓"},
            {"name": "Books & Supplies", "icon": "📖"},
            {"name": "Courses", "icon": "💻"},
        ],
    },
    # Uncategorized
    {
        "name": "Uncategorized",
        "category_type": "both",
        "icon": "❓",
        "color": "#6B7280",
        "children": [],
    },
]


@transaction.atomic
def create_default_categories(*, household: Household) -> List[Category]:
    """
    Create default system categories for a new household.

    Args:
        household: Household to create categories for

    Returns:
        List[Category]: Created category instances
    """
    created_categories = []

    for parent_data in DEFAULT_CATEGORIES:
        # Create parent category
        parent = Category(
            household=household,
            name=parent_data["name"],
            category_type=parent_data["category_type"],
            icon=parent_data["icon"],
            color=parent_data["color"],
            is_system=True,
            display_order=len(created_categories),
        )
        parent.full_clean()
        parent.save()
        created_categories.append(parent)

        # Create child categories
        for idx, child_data in enumerate(parent_data.get("children", [])):
            child = Category(
                household=household,
                name=child_data["name"],
                category_type=parent_data["category_type"],
                icon=child_data["icon"],
                color=parent_data["color"],
                parent=parent,
                is_system=True,
                display_order=idx,
            )
            child.full_clean()
            child.save()
            created_categories.append(child)

    return created_categories


@transaction.atomic
def category_soft_delete(*, category: Category) -> Category:
    """
    Soft delete a category (preserves transaction history).

    Args:
        category: Category to delete

    Returns:
        Category: Updated category instance
    """
    category.is_deleted = True
    category.is_active = False
    category.save(update_fields=["is_deleted", "is_active", "updated_at"])

    return category
