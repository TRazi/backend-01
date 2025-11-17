"""
Integration tests for AuditLog ViewSet API endpoints.
"""

import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import User
from apps.audit.models import AuditLog


@pytest.mark.django_db
class TestAuditLogViewSetList:
    """Test audit log list endpoint."""

    def test_list_audit_logs_as_staff(self):
        """Staff users can list audit logs."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        AuditLog.objects.create(
            user=user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
            object_id=1,
            ip_address="192.168.1.1",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="UPDATE",
            action_description="Updated user",
            object_type="User",
            object_id=2,
            ip_address="192.168.1.2",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_list_audit_logs_as_regular_user(self):
        """Regular users cannot access audit logs."""
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get("/api/v1/audit-logs/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_audit_logs_unauthenticated(self):
        """Unauthenticated users cannot access audit logs."""
        client = APIClient()
        response = client.get("/api/v1/audit-logs/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_audit_logs_ordered_by_created_at_desc(self):
        """Audit logs are ordered by created_at descending (newest first)."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )
        log2 = AuditLog.objects.create(
            user=admin_user,
            action_type="UPDATE",
            action_description="Updated goal",
            object_type="Goal",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/")

        assert response.status_code == status.HTTP_200_OK
        # Most recent should be first
        assert response.data[0]["id"] == log2.id


@pytest.mark.django_db
class TestAuditLogViewSetFiltering:
    """Test audit log filtering capabilities."""

    def test_filter_by_user(self):
        """Staff can filter audit logs by user."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="testpass123",
        )
        user2 = User.objects.create_user(
            email="user2@test.com",
            password="testpass123",
        )

        AuditLog.objects.create(
            user=user1,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )
        AuditLog.objects.create(
            user=user2,
            action_type="UPDATE",
            action_description="Updated goal",
            object_type="Goal",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/audit-logs/?user={user1.id}")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_filter_by_action_type(self):
        """Staff can filter audit logs by action type."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="UPDATE",
            action_description="Updated goal",
            object_type="Goal",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="DELETE",
            action_description="Deleted bill",
            object_type="Bill",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/?action_type=CREATE")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_search_by_action_type(self):
        """Staff can search audit logs by action type."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="UPDATE",
            action_description="Updated goal",
            object_type="Goal",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/?search=CREATE")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_search_by_ip_address(self):
        """Staff can search audit logs by IP address."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
            ip_address="192.168.1.1",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="UPDATE",
            action_description="Updated goal",
            object_type="Goal",
            ip_address="10.0.0.1",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/?search=192.168")

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


@pytest.mark.django_db
class TestAuditLogViewSetOrdering:
    """Test audit log ordering capabilities."""

    def test_order_by_created_at_ascending(self):
        """Staff can order audit logs by created_at ascending."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        log1 = AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created B1",
            object_type="B1",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created B2",
            object_type="B2",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/?ordering=created_at")

        assert response.status_code == status.HTTP_200_OK
        # Oldest first
        assert response.data[0]["id"] == log1.id

    def test_order_by_action_type(self):
        """Staff can order audit logs by action_type."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        AuditLog.objects.create(
            user=admin_user,
            action_type="UPDATE",
            action_description="Updated B1",
            object_type="B1",
        )
        AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created B2",
            object_type="B2",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get("/api/v1/audit-logs/?ordering=action_type")

        assert response.status_code == status.HTTP_200_OK
        # Should be alphabetically sorted
        assert response.data[0]["action_type"] == "CREATE"


@pytest.mark.django_db
class TestAuditLogViewSetRetrieve:
    """Test audit log retrieve endpoint."""

    def test_retrieve_audit_log_as_staff(self):
        """Staff users can retrieve audit log details."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        log = AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
            object_id=123,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.get(f"/api/v1/audit-logs/{log.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["action_type"] == "CREATE"
        assert response.data["object_type"] == "Budget"

    def test_retrieve_audit_log_as_regular_user(self):
        """Regular users cannot retrieve audit logs."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        user = User.objects.create_user(
            email="user@test.com",
            password="testpass123",
        )
        log = AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )

        client = APIClient()
        client.force_authenticate(user=user)
        response = client.get(f"/api/v1/audit-logs/{log.id}/")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestAuditLogViewSetReadOnly:
    """Test that AuditLogViewSet is read-only."""

    def test_create_audit_log_not_allowed(self):
        """Creating audit logs via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.post(
            "/api/v1/audit-logs/",
            {
                "user": admin_user.id,
                "action_type": "CREATE",
                "action_description": "Created budget",
                "object_type": "Budget",
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_update_audit_log_not_allowed(self):
        """Updating audit logs via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        log = AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.put(
            f"/api/v1/audit-logs/{log.id}/",
            {
                "action_type": "UPDATE",
            },
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_audit_log_not_allowed(self):
        """Deleting audit logs via ViewSet is not allowed."""
        admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )
        log = AuditLog.objects.create(
            user=admin_user,
            action_type="CREATE",
            action_description="Created budget",
            object_type="Budget",
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)
        response = client.delete(f"/api/v1/audit-logs/{log.id}/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
