# apps/households/tests/test_household_admin.py
import pytest
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory

from households.admin import HouseholdAdmin, MembershipAdmin, MembershipInline
from households.models import Household, Membership
from users.models import User


@pytest.mark.django_db
class TestHouseholdAdmin:
    """Test suite for HouseholdAdmin."""

    def test_list_display_fields(self):
        """Test list_display configuration."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert "name" in admin.list_display
        assert "household_type" in admin.list_display
        assert "budget_cycle" in admin.list_display
        assert "member_count" in admin.list_display
        assert "created_at" in admin.list_display

    def test_list_filter_fields(self):
        """Test list_filter configuration."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert "household_type" in admin.list_filter
        assert "budget_cycle" in admin.list_filter
        assert "created_at" in admin.list_filter

    def test_search_fields(self):
        """Test search_fields configuration."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert "name" in admin.search_fields

    def test_inlines_configured(self):
        """Test MembershipInline is configured."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert len(admin.inlines) == 1
        assert admin.inlines[0] == MembershipInline

    def test_readonly_fields(self):
        """Test readonly_fields configuration."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_member_count_display(self):
        """Test member_count custom method."""
        household = Household.objects.create(name="Test Household")
        user1 = User.objects.create_user(email="user1@example.com", password="pass123")
        user2 = User.objects.create_user(email="user2@example.com", password="pass123")

        # Create active memberships
        Membership.objects.create(
            household=household, user=user1, role="admin", status="active"
        )
        Membership.objects.create(
            household=household, user=user2, role="parent", status="active"
        )
        # Create inactive membership
        Membership.objects.create(
            household=household,
            user=User.objects.create_user(
                email="inactive@example.com", password="pass123"
            ),
            role="observer",
            status="inactive",
        )

        admin = HouseholdAdmin(Household, AdminSite())
        count = admin.member_count(household)

        assert count == 2  # Only active members

    def test_member_count_short_description(self):
        """Test member_count display name."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert admin.member_count.short_description == "Active Members"

    def test_fieldsets_structure(self):
        """Test fieldsets configuration."""
        admin = HouseholdAdmin(Household, AdminSite())
        assert len(admin.fieldsets) == 2

        # Check Basic Information section
        assert admin.fieldsets[0][0] == "Basic Information"
        assert "name" in admin.fieldsets[0][1]["fields"]
        assert "household_type" in admin.fieldsets[0][1]["fields"]

        # Check Timestamps section
        assert admin.fieldsets[1][0] == "Timestamps"
        assert "created_at" in admin.fieldsets[1][1]["fields"]


@pytest.mark.django_db
class TestMembershipAdmin:
    """Test suite for MembershipAdmin."""

    def test_list_display_fields(self):
        """Test list_display configuration."""
        admin = MembershipAdmin(Membership, AdminSite())
        assert "user" in admin.list_display
        assert "household" in admin.list_display
        assert "membership_type" in admin.list_display
        assert "role" in admin.list_display
        assert "status" in admin.list_display
        assert "is_primary" in admin.list_display
        assert "start_date" in admin.list_display

    def test_list_filter_fields(self):
        """Test list_filter configuration."""
        admin = MembershipAdmin(Membership, AdminSite())
        assert "membership_type" in admin.list_filter
        assert "role" in admin.list_filter
        assert "status" in admin.list_filter
        assert "is_primary" in admin.list_filter

    def test_search_fields(self):
        """Test search_fields configuration."""
        admin = MembershipAdmin(Membership, AdminSite())
        assert "user__email" in admin.search_fields
        assert "household__name" in admin.search_fields

    def test_autocomplete_fields(self):
        """Test autocomplete_fields configuration."""
        admin = MembershipAdmin(Membership, AdminSite())
        assert "user" in admin.autocomplete_fields
        assert "household" in admin.autocomplete_fields
        assert "organisation" in admin.autocomplete_fields

    def test_readonly_fields(self):
        """Test readonly_fields configuration."""
        admin = MembershipAdmin(Membership, AdminSite())
        assert "start_date" in admin.readonly_fields
        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_queryset_optimization(self):
        """Test get_queryset uses select_related for performance."""
        household = Household.objects.create(name="Test Household")
        user = User.objects.create_user(email="test@example.com", password="pass123")
        Membership.objects.create(household=household, user=user, role="admin")

        admin = MembershipAdmin(Membership, AdminSite())
        request = RequestFactory().get("/admin/households/membership/")
        queryset = admin.get_queryset(request)

        # Check that select_related is applied
        assert "user" in queryset.query.select_related
        assert "household" in queryset.query.select_related


@pytest.mark.django_db
class TestMembershipInline:
    """Test suite for MembershipInline."""

    def test_inline_model(self):
        """Test inline model is Membership."""
        inline = MembershipInline(Household, AdminSite())
        assert inline.model == Membership

    def test_extra_forms(self):
        """Test no extra forms by default."""
        inline = MembershipInline(Household, AdminSite())
        assert inline.extra == 0

    def test_fields_configuration(self):
        """Test fields shown in inline."""
        inline = MembershipInline(Household, AdminSite())
        assert "user" in inline.fields
        assert "role" in inline.fields
        assert "membership_type" in inline.fields
        assert "status" in inline.fields
        assert "is_primary" in inline.fields
        assert "start_date" in inline.fields

    def test_readonly_fields_inline(self):
        """Test readonly fields in inline."""
        inline = MembershipInline(Household, AdminSite())
        assert "start_date" in inline.readonly_fields

    def test_autocomplete_fields_inline(self):
        """Test autocomplete fields in inline."""
        inline = MembershipInline(Household, AdminSite())
        assert "user" in inline.autocomplete_fields
