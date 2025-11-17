# apps/goals/tests/test_goal_admin.py
import pytest
from decimal import Decimal
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.utils import timezone

from apps.goals.admin import GoalAdmin, GoalProgressAdmin, GoalProgressInline
from apps.goals.models import Goal, GoalProgress
from apps.households.models import Household
from apps.users.models import User


@pytest.mark.django_db
class TestGoalAdmin:
    """Test suite for GoalAdmin."""

    def test_list_display_fields(self):
        """Test list_display configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert "name" in admin.list_display
        assert "household" in admin.list_display
        assert "goal_type" in admin.list_display
        assert "target_amount" in admin.list_display
        assert "current_amount" in admin.list_display
        assert "progress" in admin.list_display
        assert "due_date" in admin.list_display
        assert "status" in admin.list_display
        assert "sticker_count" in admin.list_display
        assert "created_at" in admin.list_display

    def test_list_filter_fields(self):
        """Test list_filter configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert "status" in admin.list_filter
        assert "goal_type" in admin.list_filter
        assert "due_date" in admin.list_filter
        assert "auto_contribute" in admin.list_filter
        assert "created_at" in admin.list_filter

    def test_search_fields(self):
        """Test search_fields configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert "name" in admin.search_fields
        assert "household__name" in admin.search_fields
        assert "description" in admin.search_fields

    def test_autocomplete_fields(self):
        """Test autocomplete_fields configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert "household" in admin.autocomplete_fields

    def test_date_hierarchy(self):
        """Test date_hierarchy configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert admin.date_hierarchy == "due_date"

    def test_inlines_configured(self):
        """Test GoalProgressInline is configured."""
        admin = GoalAdmin(Goal, AdminSite())
        assert len(admin.inlines) == 1
        assert admin.inlines[0] == GoalProgressInline

    def test_readonly_fields(self):
        """Test readonly_fields configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_progress_display_full(self):
        """Test progress display with 100% completion."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save $1000",
            goal_type="savings",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("1000.00"),
            due_date=timezone.now().date(),
        )

        admin = GoalAdmin(Goal, AdminSite())
        progress = admin.progress(goal)

        assert progress == "100.0%"

    def test_progress_display_partial(self):
        """Test progress display with partial completion."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save $1000",
            goal_type="savings",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("450.00"),
            due_date=timezone.now().date(),
        )

        admin = GoalAdmin(Goal, AdminSite())
        progress = admin.progress(goal)

        assert progress == "45.0%"

    def test_progress_display_zero(self):
        """Test progress display with no progress."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Save $1000",
            goal_type="savings",
            target_amount=Decimal("1000.00"),
            current_amount=Decimal("0.00"),
            due_date=timezone.now().date(),
        )

        admin = GoalAdmin(Goal, AdminSite())
        progress = admin.progress(goal)

        assert progress == "0.0%"

    def test_progress_short_description(self):
        """Test progress column name."""
        admin = GoalAdmin(Goal, AdminSite())
        assert admin.progress.short_description == "Progress"

    def test_queryset_optimization(self):
        """Test get_queryset uses select_related for performance."""
        household = Household.objects.create(name="Test Household")
        Goal.objects.create(
            household=household,
            name="Test Goal",
            goal_type="savings",
            target_amount=Decimal("500.00"),
            due_date=timezone.now().date(),
        )

        admin = GoalAdmin(Goal, AdminSite())
        request = RequestFactory().get("/admin/goals/goal/")
        queryset = admin.get_queryset(request)

        # Check that select_related is applied
        assert "household" in queryset.query.select_related

    def test_fieldsets_structure(self):
        """Test fieldsets configuration."""
        admin = GoalAdmin(Goal, AdminSite())
        assert len(admin.fieldsets) == 7

        # Check Basic Information section
        assert admin.fieldsets[0][0] == "Basic Information"
        assert "household" in admin.fieldsets[0][1]["fields"]
        assert "name" in admin.fieldsets[0][1]["fields"]

        # Check Financial Targets section
        assert admin.fieldsets[1][0] == "Financial Targets"
        assert "target_amount" in admin.fieldsets[1][1]["fields"]

        # Check Gamification section (collapsed)
        assert admin.fieldsets[2][0] == "Gamification"
        assert "collapse" in admin.fieldsets[2][1]["classes"]
        assert "sticker_count" in admin.fieldsets[2][1]["fields"]

        # Check Auto Contribution section (collapsed)
        assert admin.fieldsets[3][0] == "Auto Contribution"
        assert "collapse" in admin.fieldsets[3][1]["classes"]

        # Check Display section (collapsed)
        assert admin.fieldsets[4][0] == "Display"
        assert "collapse" in admin.fieldsets[4][1]["classes"]


@pytest.mark.django_db
class TestGoalProgressAdmin:
    """Test suite for GoalProgressAdmin."""

    def test_list_display_fields(self):
        """Test list_display configuration."""
        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        assert "goal" in admin.list_display
        assert "amount_added" in admin.list_display
        assert "date_added" in admin.list_display
        assert "milestone_reached" in admin.list_display
        assert "transaction" in admin.list_display
        assert "created_at" in admin.list_display

    def test_list_filter_fields(self):
        """Test list_filter configuration."""
        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        assert "milestone_reached" in admin.list_filter
        assert "date_added" in admin.list_filter
        assert "created_at" in admin.list_filter

    def test_search_fields(self):
        """Test search_fields configuration."""
        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        assert "goal__name" in admin.search_fields
        assert "notes" in admin.search_fields

    def test_autocomplete_fields(self):
        """Test autocomplete_fields configuration."""
        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        assert "goal" in admin.autocomplete_fields
        assert "transaction" in admin.autocomplete_fields

    def test_date_hierarchy(self):
        """Test date_hierarchy configuration."""
        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        assert admin.date_hierarchy == "date_added"

    def test_readonly_fields(self):
        """Test readonly_fields configuration."""
        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        assert "date_added" in admin.readonly_fields
        assert "created_at" in admin.readonly_fields
        assert "updated_at" in admin.readonly_fields

    def test_queryset_optimization(self):
        """Test get_queryset uses select_related for performance."""
        household = Household.objects.create(name="Test Household")
        goal = Goal.objects.create(
            household=household,
            name="Test Goal",
            goal_type="savings",
            target_amount=Decimal("500.00"),
            due_date=timezone.now().date(),
        )
        GoalProgress.objects.create(
            goal=goal,
            amount_added=Decimal("100.00"),
        )

        admin = GoalProgressAdmin(GoalProgress, AdminSite())
        request = RequestFactory().get("/admin/goals/goalprogress/")
        queryset = admin.get_queryset(request)

        # Check that select_related is applied
        assert "goal" in queryset.query.select_related
        assert "transaction" in queryset.query.select_related


@pytest.mark.django_db
class TestGoalProgressInline:
    """Test suite for GoalProgressInline."""

    def test_inline_model(self):
        """Test inline model is GoalProgress."""
        inline = GoalProgressInline(Goal, AdminSite())
        assert inline.model == GoalProgress

    def test_extra_forms(self):
        """Test no extra forms by default."""
        inline = GoalProgressInline(Goal, AdminSite())
        assert inline.extra == 0

    def test_fields_configuration(self):
        """Test fields shown in inline."""
        inline = GoalProgressInline(Goal, AdminSite())
        assert "amount_added" in inline.fields
        assert "date_added" in inline.fields
        assert "milestone_reached" in inline.fields
        assert "notes" in inline.fields

    def test_readonly_fields_inline(self):
        """Test readonly fields in inline."""
        inline = GoalProgressInline(Goal, AdminSite())
        assert "date_added" in inline.readonly_fields
