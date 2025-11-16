"""
Integration tests for Budget and BudgetItem ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date

from users.models import User
from households.models import Household
from budgets.models import Budget, BudgetItem
from categories.models import Category


@pytest.mark.django_db
class TestBudgetViewSetList:
    """Test budget list endpoint."""

    def test_list_budgets_authenticated(self):
        """Authenticated users see their household's budgets."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        Budget.objects.create(
            household=household,
            name="Monthly Budget",
            total_amount=Decimal("3000.00"),
            cycle_type="monthly",
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/budgets/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Monthly Budget"

    def test_list_budgets_household_isolation(self):
        """Users only see budgets from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
            household=household1,
        )

        Budget.objects.create(
            household=household1,
            name="Budget 1",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        Budget.objects.create(
            household=household2,
            name="Budget 2",
            total_amount=Decimal("2000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/budgets/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["name"] == "Budget 1"

    def test_list_budgets_staff_sees_all(self):
        """Staff users see all budgets."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        Budget.objects.create(
            household=household1,
            name="B1",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        Budget.objects.create(
            household=household2,
            name="B2",
            total_amount=Decimal("2000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/budgets/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


@pytest.mark.django_db
class TestBudgetViewSetCreate:
    """Test budget create endpoint."""

    def test_create_budget(self):
        """Users can create budgets for their household."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/budgets/",
            {
                "household": household.id,
                "name": "New Budget",
                "total_amount": "5000.00",
                "cycle_type": "monthly",
                "start_date": "2025-01-01",
                "end_date": "2025-01-31",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Budget"
        assert Budget.objects.count() == 1


@pytest.mark.django_db
class TestBudgetViewSetCustomActions:
    """Test budget custom actions."""

    def test_utilization_action(self):
        """Test GET /budgets/{id}/utilization/ returns budget utilization data."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            total_amount=Decimal("1000.00"),
            cycle_type="monthly",
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/budgets/{budget.id}/utilization/")

        assert response.status_code == status.HTTP_200_OK
        assert "name" in response.data
        assert "total_amount" in response.data

    def test_add_item_action(self):
        """Test POST /budgets/{id}/items/ creates a budget item."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="Test Budget",
            total_amount=Decimal("1000.00"),
            cycle_type="monthly",
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        category = Category.objects.create(
            household=household,
            name="Groceries",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            f"/api/v1/budgets/{budget.id}/items/",
            {
                "name": "Groceries Budget",
                "category": category.id,
                "amount": "200.00",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert BudgetItem.objects.count() == 1
        assert BudgetItem.objects.first().budget == budget


@pytest.mark.django_db
class TestBudgetItemViewSetList:
    """Test budget item list endpoint."""

    def test_list_budget_items_authenticated(self):
        """Users see budget items from their household."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        category = Category.objects.create(household=household, name="Food")
        BudgetItem.objects.create(
            budget=budget,
            category=category,
            amount=Decimal("500"),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/budget-items/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_list_budget_items_household_isolation(self):
        """Users only see items from their own household."""
        household1 = Household.objects.create(name="Family 1")
        household2 = Household.objects.create(name="Family 2")

        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
            household=household1,
        )

        budget1 = Budget.objects.create(
            household=household1,
            name="B1",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        budget2 = Budget.objects.create(
            household=household2,
            name="B2",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )

        cat1 = Category.objects.create(household=household1, name="C1")
        cat2 = Category.objects.create(household=household2, name="C2")

        BudgetItem.objects.create(budget=budget1, category=cat1, amount=Decimal("100"))
        BudgetItem.objects.create(budget=budget2, category=cat2, amount=Decimal("200"))

        client = APIClient()
        client.force_authenticate(user=user1)
        response = client.get("/api/v1/budget-items/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


@pytest.mark.django_db
class TestBudgetItemViewSetCreate:
    """Test budget item create endpoint."""

    def test_create_budget_item(self):
        """Users can create budget items."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        category = Category.objects.create(household=household, name="Transport")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/budget-items/",
            {
                "name": "Transport Budget",
                "budget": budget.id,
                "category": category.id,
                "amount": "150.00",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert BudgetItem.objects.count() == 1

    def test_create_budget_item_uses_create_serializer(self):
        """Budget item create uses BudgetItemCreateSerializer."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="Budget",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        category = Category.objects.create(household=household, name="Food")

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            "/api/v1/budget-items/",
            {
                "name": "Food Budget",
                "budget": budget.id,
                "category": category.id,
                "amount": "300.00",
            },
        )

        assert response.status_code == status.HTTP_201_CREATED
        item = BudgetItem.objects.first()
        assert item.budget == budget
        assert item.category == category


@pytest.mark.django_db
class TestBudgetItemViewSetUpdate:
    """Test budget item update endpoint."""

    def test_update_budget_item(self):
        """Users can update their household's budget items."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="B",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        category = Category.objects.create(household=household, name="C")
        item = BudgetItem.objects.create(
            budget=budget,
            category=category,
            amount=Decimal("100"),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.patch(
            f"/api/v1/budget-items/{item.id}/",
            {
                "amount": "250.00",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["amount"] == "250.00"


@pytest.mark.django_db
class TestBudgetItemViewSetDelete:
    """Test budget item delete endpoint."""

    def test_delete_budget_item(self):
        """Users can delete their household's budget items."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
            household=household,
        )
        budget = Budget.objects.create(
            household=household,
            name="B",
            total_amount=Decimal("1000"),
            start_date="2025-01-01",
            end_date="2025-01-31",
        )
        category = Category.objects.create(household=household, name="C")
        item = BudgetItem.objects.create(
            budget=budget,
            category=category,
            amount=Decimal("100"),
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.delete(f"/api/v1/budget-items/{item.id}/")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert BudgetItem.objects.count() == 0
