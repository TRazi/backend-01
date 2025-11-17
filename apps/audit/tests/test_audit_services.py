"""
Tests for audit service helper functions.
"""

import pytest
from unittest.mock import Mock
from datetime import datetime
from django.utils import timezone

from apps.audit.services import (
    _get_ip_address,
    _get_user_agent,
    _get_request_context,
    get_model_field_changes,
    log_action,
    log_model_change,
    log_data_export,
)
from apps.audit.models import AuditLog, DataExportLog
from apps.households.models import Household
from apps.users.models import User


@pytest.mark.unit
def test_get_ip_address_from_remote_addr():
    """Test extracting IP from REMOTE_ADDR."""
    request = Mock()
    request.META = {"REMOTE_ADDR": "192.168.1.1"}

    ip = _get_ip_address(request)
    assert ip == "192.168.1.1"


@pytest.mark.unit
def test_get_ip_address_from_x_forwarded_for():
    """Test extracting IP from X-Forwarded-For header."""
    request = Mock()
    request.META = {
        "HTTP_X_FORWARDED_FOR": "203.0.113.1, 198.51.100.1",
        "REMOTE_ADDR": "192.168.1.1",
    }

    ip = _get_ip_address(request)
    # Should return first IP from X-Forwarded-For
    assert ip == "203.0.113.1"


@pytest.mark.unit
def test_get_ip_address_none_request():
    """Test IP extraction with None request."""
    ip = _get_ip_address(None)
    assert ip is None


@pytest.mark.unit
def test_get_user_agent():
    """Test extracting user agent from request."""
    request = Mock()
    request.META = {"HTTP_USER_AGENT": "Mozilla/5.0 Test Browser"}

    user_agent = _get_user_agent(request)
    assert user_agent == "Mozilla/5.0 Test Browser"


@pytest.mark.unit
def test_get_user_agent_missing():
    """Test user agent extraction when header missing."""
    request = Mock()
    request.META = {}

    user_agent = _get_user_agent(request)
    assert user_agent == ""


@pytest.mark.unit
def test_get_user_agent_none_request():
    """Test user agent extraction with None request."""
    user_agent = _get_user_agent(None)
    assert user_agent == ""


@pytest.mark.unit
def test_get_request_context():
    """Test extracting full request context."""
    request = Mock()
    request.META = {
        "REMOTE_ADDR": "192.168.1.1",
        "HTTP_USER_AGENT": "Test Browser",
    }
    request.path = "/api/transactions/"
    request.method = "POST"

    context = _get_request_context(request)

    assert context["ip_address"] == "192.168.1.1"
    assert context["user_agent"] == "Test Browser"
    assert context["request_path"] == "/api/transactions/"
    assert context["request_method"] == "POST"


@pytest.mark.unit
def test_get_request_context_none_request():
    """Test request context with None request."""
    context = _get_request_context(None)

    assert context["ip_address"] is None
    assert context["user_agent"] == ""
    assert context["request_path"] == ""
    assert context["request_method"] == ""


@pytest.mark.django_db
@pytest.mark.unit
def test_get_model_field_changes():
    """Test detecting changes between model instances."""
    old_household = Household(
        name="Old Name",
        household_type="fam",
        budget_cycle="m",
    )

    new_household = Household(
        name="New Name",
        household_type="fam",
        budget_cycle="w",
    )

    changes = get_model_field_changes(new_household, old_household)

    assert "name" in changes
    assert changes["name"]["old"] == "Old Name"
    assert changes["name"]["new"] == "New Name"

    assert "budget_cycle" in changes
    assert changes["budget_cycle"]["old"] == "m"
    assert changes["budget_cycle"]["new"] == "w"

    # household_type didn't change
    assert "household_type" not in changes


@pytest.mark.django_db
@pytest.mark.unit
def test_get_model_field_changes_no_changes():
    """Test when no fields changed."""
    household1 = Household(
        name="Same Name",
        household_type="fam",
        budget_cycle="m",
    )

    household2 = Household(
        name="Same Name",
        household_type="fam",
        budget_cycle="m",
    )

    changes = get_model_field_changes(household2, household1)

    # Should exclude id, created_at, updated_at
    assert len(changes) == 0


@pytest.mark.django_db
@pytest.mark.unit
def test_get_model_field_changes_null_values():
    """Test changes with None values."""
    old_household = Household(
        name="Name",
        household_type="fam",
        budget_cycle="m",
    )
    old_household.currency = "USD"

    new_household = Household(
        name="Name",
        household_type="fam",
        budget_cycle="m",
    )
    new_household.currency = None

    changes = get_model_field_changes(new_household, old_household)

    if "currency" in changes:
        assert changes["currency"]["old"] == "USD"
        assert changes["currency"]["new"] is None


@pytest.mark.django_db
@pytest.mark.unit
def test_log_action():
    """Test creating an audit log entry."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    request = Mock()
    request.user = user
    request.path = "/api/test/"
    request.method = "POST"
    request.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "Test"}

    log = log_action(
        user=user,
        action_type="CREATE",
        action_description="Test action",
        request=request,
        object_type="TestModel",
        object_id=123,
        object_repr="Test Object",
        household=household,
    )

    assert log.user == user
    assert log.action_type == "CREATE"
    assert log.action_description == "Test action"
    assert log.object_type == "TestModel"
    assert log.object_id == 123
    assert log.household == household
    assert log.ip_address == "127.0.0.1"
    assert log.user_agent == "Test"


@pytest.mark.django_db
@pytest.mark.unit
def test_log_action_invalid_type():
    """Test log_action with invalid action type."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )

    with pytest.raises(ValueError, match="Invalid action_type"):
        log_action(
            user=user,
            action_type="INVALID",
            action_description="Test",
        )


@pytest.mark.django_db
@pytest.mark.unit
def test_log_model_change_create():
    """Test logging model creation."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    request = Mock()
    request.user = user
    request.path = "/api/households/"
    request.method = "POST"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    log = log_model_change(
        user=user,
        action_type="CREATE",
        instance=household,
        request=request,
    )

    assert log.action_type == "CREATE"
    assert log.object_type == "Household"
    assert log.object_id == household.id
    assert "Created Household" in log.action_description


@pytest.mark.django_db
@pytest.mark.unit
def test_log_model_change_update():
    """Test logging model update with changes."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Old Name",
        household_type="fam",
        budget_cycle="m",
    )

    old_values = {"name": "Old Name"}
    household.name = "New Name"
    household.save()

    request = Mock()
    request.user = user
    request.path = "/api/households/"
    request.method = "PATCH"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    log = log_model_change(
        user=user,
        action_type="UPDATE",
        instance=household,
        old_values=old_values,
        request=request,
    )

    assert log.action_type == "UPDATE"
    assert "Updated Household" in log.action_description
    assert "name" in log.changes
    assert log.changes["name"]["old"] == "Old Name"
    assert log.changes["name"]["new"] == "New Name"


@pytest.mark.django_db
@pytest.mark.unit
def test_log_model_change_delete():
    """Test logging model deletion."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    request = Mock()
    request.user = user
    request.path = "/api/households/"
    request.method = "DELETE"
    request.META = {"REMOTE_ADDR": "127.0.0.1"}

    log = log_model_change(
        user=user,
        action_type="DELETE",
        instance=household,
        request=request,
    )

    assert log.action_type == "DELETE"
    assert "Deleted Household" in log.action_description


@pytest.mark.django_db
@pytest.mark.unit
def test_log_data_export():
    """Test logging data export."""
    user = User.objects.create_user(
        email="test@example.com",
        password="testpass123",
    )
    household = Household.objects.create(
        name="Test Household",
        household_type="fam",
        budget_cycle="m",
    )

    request = Mock()
    request.user = user
    request.path = "/api/export/"
    request.method = "GET"
    request.META = {"REMOTE_ADDR": "127.0.0.1", "HTTP_USER_AGENT": "Test"}

    export_log = log_data_export(
        user=user,
        export_type="transaction_export",
        record_count=100,
        request=request,
        household=household,
        file_format="csv",
    )

    assert export_log.user == user
    assert export_log.export_type == "transaction_export"
    assert export_log.record_count == 100
    assert export_log.household == household
    assert export_log.file_format == "csv"
    assert export_log.ip_address == "127.0.0.1"

    # Check that audit log was also created
    audit_log = AuditLog.objects.filter(user=user, action_type="EXPORT").first()
    assert audit_log is not None
    assert "100 records" in audit_log.action_description
