# apps/users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils import timezone
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from users.models import EmailOTP, EmailVerification, AccountUnlockToken


def get_user_model_lazy():
    from django.contrib.auth import get_user_model

    return get_user_model()


User = get_user_model_lazy()


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    """Admin interface for User model."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = [
        "email",
        "username",
        "first_name",
        "last_name",
        "household",
        "role",
        "email_verified",
        "is_active",
        "is_staff",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "is_staff",
        "is_superuser",
        "email_verified",
        "role",
        "created_at",
    ]

    search_fields = [
        "email",
        "username",
        "first_name",
        "last_name",
        "phone_number",
    ]

    ordering = ["-created_at"]

    fieldsets = (
        (
            "Authentication",
            {"fields": ("email", "username", "password", "email_verified")},
        ),
        (
            "Personal Info",
            {"fields": ("first_name", "last_name", "phone_number", "locale")},
        ),
        ("Household & Role", {"fields": ("household", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Technical Details",
            {
                "fields": ("uuid",),
                "classes": ("collapse",),
            },
        ),
        (
            "Important Dates",
            {
                "fields": ("last_login", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            "Create User",
            {
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_active",
                )
            },
        ),
    )

    readonly_fields = ["uuid", "created_at", "updated_at", "last_login"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("household")


@admin.register(EmailOTP)
class EmailOTPAdmin(ModelAdmin):
    """Admin interface for Email OTP codes."""

    list_display = [
        "user_email",
        "code_display",
        "status_badge",
        "ip_address",
        "time_until_expiry",
        "created_at",
    ]

    list_filter = [
        "is_used",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "code",
        "ip_address",
    ]

    ordering = ["-created_at"]

    readonly_fields = [
        "user",
        "code",
        "expires_at",
        "is_used",
        "ip_address",
        "created_at",
        "status_badge",
        "time_until_expiry",
    ]

    fieldsets = (
        (
            "OTP Details",
            {
                "fields": (
                    "user",
                    "code",
                    "status_badge",
                )
            },
        ),
        (
            "Status & Expiry",
            {
                "fields": (
                    "is_used",
                    "expires_at",
                    "time_until_expiry",
                )
            },
        ),
        (
            "Security",
            {
                "fields": ("ip_address",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        # Optimize queries by selecting related user
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request):
        # Prevent manual creation of OTP codes in admin
        return False

    def has_change_permission(self, request, obj=None):
        # Make all fields read-only
        return False

    def user_email(self, obj):
        """Display user's email address."""
        return obj.user.email

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"

    def code_display(self, obj):
        """Display OTP code with monospace font."""
        return format_html(
            '<code style="font-size: 14px; font-weight: bold; letter-spacing: 2px;">{}</code>',
            obj.code,
        )

    code_display.short_description = "OTP Code"

    def status_badge(self, obj):
        """Display colored status badge based on OTP state."""
        if obj.is_used:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">USED</span>'
            )
        elif obj.is_valid():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">VALID</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">EXPIRED</span>'
            )

    status_badge.short_description = "Status"

    def time_until_expiry(self, obj):
        """Display time remaining until OTP expires or time since expiry."""
        now = timezone.now()
        if obj.is_used:
            return "N/A (Used)"

        if now < obj.expires_at:
            delta = obj.expires_at - now
            minutes = int(delta.total_seconds() / 60)
            seconds = int(delta.total_seconds() % 60)
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} min {} sec</span>',
                minutes,
                seconds,
            )
        else:
            delta = now - obj.expires_at
            minutes = int(delta.total_seconds() / 60)
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired {} min ago</span>',
                minutes,
            )

    time_until_expiry.short_description = "Time Until Expiry"


@admin.register(EmailVerification)
class EmailVerificationAdmin(ModelAdmin):
    """Admin interface for Email Verification tokens."""

    list_display = [
        "user_email",
        "token_preview",
        "status_badge",
        "time_since_creation",
        "verified_at",
        "created_at",
    ]

    list_filter = [
        "verified_at",
        "created_at",
    ]

    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "token",
    ]

    ordering = ["-created_at"]

    readonly_fields = [
        "user",
        "token",
        "verified_at",
        "created_at",
        "status_badge",
        "time_since_creation",
    ]

    fieldsets = (
        (
            "Verification Details",
            {
                "fields": (
                    "user",
                    "token",
                    "status_badge",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "verified_at",
                    "time_since_creation",
                )
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        # Optimize queries by selecting related user
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request):
        # Prevent manual creation of verification tokens in admin
        return False

    def has_change_permission(self, request, obj=None):
        # Make all fields read-only
        return False

    def user_email(self, obj):
        """Display user's email address."""
        return obj.user.email

    user_email.short_description = "User Email"
    user_email.admin_order_field = "user__email"

    def token_preview(self, obj):
        """Display first 8 characters of token for security."""
        token_str = str(obj.token)
        return format_html(
            '<code style="font-size: 12px;">{}&hellip;</code>', token_str[:8]
        )

    token_preview.short_description = "Token"

    def status_badge(self, obj):
        """Display colored status badge based on verification state."""
        if obj.is_verified():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">✓ VERIFIED</span>'
            )
        elif obj.is_expired():
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">⏱ EXPIRED</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #ffc107; color: #000; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">⏳ PENDING</span>'
            )

    status_badge.short_description = "Status"

    def time_since_creation(self, obj):
        """Display time elapsed since token creation."""
        now = timezone.now()
        delta = now - obj.created_at
        hours = int(delta.total_seconds() / 3600)
        minutes = int((delta.total_seconds() % 3600) / 60)

        if obj.is_expired() and not obj.is_verified():
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{} hours {} min (Expired)</span>',
                hours,
                minutes,
            )
        elif obj.is_verified():
            return format_html(
                '<span style="color: #6c757d;">{} hours {} min</span>', hours, minutes
            )
        else:
            remaining_hours = 24 - hours
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} hours {} min ({} hours left)</span>',
                hours,
                minutes,
                remaining_hours,
            )

    time_since_creation.short_description = "Time Since Creation"


@admin.register(AccountUnlockToken)
class AccountUnlockTokenAdmin(ModelAdmin):
    """Admin interface for Account Unlock Tokens."""

    list_display = [
        "email",
        "token_preview",
        "status_badge",
        "ip_address",
        "time_until_expiry",
        "created_at",
    ]

    list_filter = [
        "used_at",
        "created_at",
    ]

    search_fields = [
        "email",
        "token",
        "ip_address",
    ]

    ordering = ["-created_at"]

    readonly_fields = [
        "email",
        "token",
        "expires_at",
        "used_at",
        "ip_address",
        "created_at",
        "status_badge",
        "time_until_expiry",
    ]

    fieldsets = (
        (
            "Unlock Token Details",
            {
                "fields": (
                    "email",
                    "token",
                    "status_badge",
                )
            },
        ),
        (
            "Status & Expiry",
            {
                "fields": (
                    "used_at",
                    "expires_at",
                    "time_until_expiry",
                )
            },
        ),
        (
            "Security",
            {
                "fields": ("ip_address",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request):
        # Prevent manual creation of unlock tokens in admin
        return False

    def has_change_permission(self, request, obj=None):
        # Make all fields read-only
        return False

    def token_preview(self, obj):
        """Display first 8 characters of token for security."""
        token_str = str(obj.token)
        return format_html(
            '<code style="font-size: 12px;">{}&hellip;</code>', token_str[:8]
        )

    token_preview.short_description = "Token"

    def status_badge(self, obj):
        """Display colored status badge based on token validity."""
        if obj.used_at:
            return format_html(
                '<span style="background-color: #6c757d; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">USED</span>'
            )
        elif obj.is_valid():
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">VALID</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px; font-weight: bold;">EXPIRED</span>'
            )

    status_badge.short_description = "Status"

    def time_until_expiry(self, obj):
        """Display time remaining until token expires or time since expiry."""
        now = timezone.now()
        if obj.used_at:
            return "N/A (Used)"

        if now < obj.expires_at:
            delta = obj.expires_at - now
            minutes = int(delta.total_seconds() / 60)
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">{} min remaining</span>',
                minutes,
            )
        else:
            delta = now - obj.expires_at
            minutes = int(delta.total_seconds() / 60)
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired {} min ago</span>',
                minutes,
            )

    time_until_expiry.short_description = "Time Until Expiry"
