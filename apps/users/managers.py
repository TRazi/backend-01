# apps/users/managers.py
from django.contrib.auth.models import BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom user manager for email-based and username-based authentication.

    Supports creating users with email or username, both normalized and unique.
    """

    def create_user(self, email=None, username=None, password=None, **extra_fields):
        """
        Create and save a regular user with the given email/username and password.

        Either email or username must be provided.
        """
        if not email and not username:
            raise ValueError("Either email or username must be set")

        if email:
            email = self.normalize_email(email).lower()
        if username:
            username = username.strip().lower()

        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email=None, username=None, password=None, **extra_fields
    ):
        """
        Create and save a superuser with the given email/username and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)
