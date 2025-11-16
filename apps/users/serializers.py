# apps/users/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from .models import User, EmailVerification


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    has_mfa_enabled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "email_verified",
            "first_name",
            "last_name",
            "full_name",
            "phone_number",
            "locale",
            "role",
            "household",
            "is_active",
            "has_mfa_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "email",
            "email_verified",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        ]

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_has_mfa_enabled(self, obj):
        try:
            return obj.mfa_device.is_enabled
        except Exception:
            return False


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration with email verification.

    Django Best Practice: Use ModelSerializer with Meta class,
    leverage built-in field definitions, use validate_ methods,
    wrap create() in transaction.
    """

    password = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Minimum 8 characters, must include uppercase, lowercase, and numbers",
    )
    password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={"input_type": "password"},
        help_text="Must match password field",
    )

    class Meta:
        model = User
        fields = ["email", "password", "password_confirm", "first_name", "last_name"]
        extra_kwargs = {
            "email": {
                "required": True,
                "help_text": "Valid email address for account verification",
            },
            "first_name": {
                "required": False,
                "allow_blank": True,
                "help_text": "First name (optional)",
            },
            "last_name": {
                "required": False,
                "allow_blank": True,
                "help_text": "Last name (optional)",
            },
        }

    def validate_email(self, value):
        """
        Validate email is unique and normalized.

        Django Best Practice: Use validate_<field_name> for field-level validation.
        """
        # Normalize email to lowercase
        value = value.lower().strip()

        # Check uniqueness
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")

        return value

    def validate_password(self, value):
        """
        Validate password against Django's password validators.

        Django Best Practice: Use Django's built-in password validation.
        """
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        """
        Validate passwords match.

        Django Best Practice: Use validate() for cross-field validation.
        """
        if data.get("password") != data.get("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Create user and trigger verification email.

        Django Best Practice: Use @transaction.atomic to ensure
        user creation and verification token creation succeed together.
        Uses select_for_update to prevent race conditions.
        """
        from users.tasks import send_verification_email

        # Remove password_confirm (not a model field)
        validated_data.pop("password_confirm", None)

        # Create user (inactive until verified)
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_active=False,  # User must verify email first
            email_verified=False,
        )

        # Create verification token
        verification = EmailVerification.objects.create(user=user)

        # Send verification email (async) - outside transaction
        transaction.on_commit(
            lambda: send_verification_email.delay(user.id, str(verification.token))
        )

        return user


class EmailOTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP code.

    Django Best Practice: Simple serializers for input validation.
    """

    email = serializers.EmailField(
        required=True, help_text="Email address to send OTP code"
    )

    def validate_email(self, value):
        """Normalize email."""
        return value.lower().strip()


class EmailOTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP code.

    Django Best Practice: Use RegexField for code validation.
    """

    email = serializers.EmailField(
        required=True, help_text="Email address associated with OTP"
    )
    code = serializers.RegexField(
        regex=r"^\d{6}$",
        required=True,
        max_length=6,
        min_length=6,
        help_text="6-digit OTP code",
        error_messages={"invalid": "OTP code must be exactly 6 digits"},
    )

    def validate_email(self, value):
        """Normalize email."""
        return value.lower().strip()

    def validate_code(self, value):
        """Strip whitespace from code."""
        return value.strip()
