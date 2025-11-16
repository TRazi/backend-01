"""Tests for Account serializers to reach 85% coverage."""

from decimal import Decimal
from unittest.mock import Mock

import pytest

from accounts.models import Account
from accounts.serializers import AccountSerializer
from households.models import Household
from users.models import User


@pytest.mark.django_db
@pytest.mark.unit
class TestAccountSerializer:
    """Test AccountSerializer edge cases."""

    def test_serializer_fields_include_all_required_fields(self):
        """Test that serializer includes all required fields."""
        serializer = AccountSerializer()

        expected_fields = [
            "id",
            "household",
            "name",
            "account_type",
            "balance",
            "institution",
            "currency",
            "created_at",
            "updated_at",
        ]

        assert set(serializer.fields.keys()) >= set(expected_fields)
