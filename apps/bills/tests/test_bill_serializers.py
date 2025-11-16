"""
Tests for Bill serializers.
"""

import pytest
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta

from users.models import User
from households.models import Household
from bills.models import Bill
from bills.serializers import BillSerializer
from rest_framework.test import APIRequestFactory


@pytest.mark.django_db
class TestBillSerializer:
    """Test BillSerializer."""

    def test_serializer_includes_computed_fields(self):
        """Serializer includes computed property fields."""
        household = Household.objects.create(name="Test Family")
        bill = Bill.objects.create(
            household=household,
            name="Rent",
            amount=Decimal("1200.00"),
            due_date=(timezone.now() + timedelta(days=5)).date(),
            status="pending",
        )

        serializer = BillSerializer(bill)
        data = serializer.data

        assert "is_overdue" in data
        assert "is_upcoming" in data
        assert "days_until_due" in data
        assert "should_send_reminder" in data

    def test_serializer_create_sets_household_from_request(self):
        """Serializer automatically sets household from request user."""
        household = Household.objects.create(name="Test Family")
        user = User.objects.create_user(
            email="user@test.com",
            password="pass123",
            first_name="User",
            household=household,
        )

        factory = APIRequestFactory()
        request = factory.post("/api/v1/bills/")
        request.user = user

        data = {
            "name": "Internet",
            "amount": "80.00",
            "due_date": timezone.now().date(),
        }

        serializer = BillSerializer(data=data, context={"request": request})
        assert serializer.is_valid()

        bill = serializer.save()
        assert bill.household == household

    def test_serializer_read_only_fields(self):
        """Certain fields are read-only."""
        household = Household.objects.create(name="Test Family")
        bill = Bill.objects.create(
            household=household, name="Bill", amount=100, due_date=timezone.now().date()
        )

        serializer = BillSerializer(bill)

        # These fields should be in read_only_fields
        read_only = serializer.Meta.read_only_fields
        assert "household" in read_only
        assert "is_overdue" in read_only
        assert "is_upcoming" in read_only
        assert "days_until_due" in read_only
        assert "should_send_reminder" in read_only
        assert "created_at" in read_only
        assert "updated_at" in read_only

    def test_serializer_includes_all_model_fields(self):
        """Serializer includes all important model fields."""
        household = Household.objects.create(name="Test Family")
        bill = Bill.objects.create(
            household=household, name="Bill", amount=100, due_date=timezone.now().date()
        )

        serializer = BillSerializer(bill)
        data = serializer.data

        assert "id" in data
        assert "name" in data
        assert "amount" in data
        assert "due_date" in data
        assert "frequency" in data
        assert "status" in data
        assert "is_recurring" in data
