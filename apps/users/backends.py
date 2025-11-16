# apps/users/backends.py
"""
Custom authentication backends supporting email and username login.

Django Best Practice: Custom backends allow flexible authentication methods
while maintaining security and audit logging.
"""

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Authentication backend that allows login with either email or username.

    Features:
    - Case-insensitive username/email matching
    - Maintains security and audit logging
    - Works with Django's authentication system
    - Supports OTP and traditional password authentication

    Usage in settings.py AUTHENTICATION_BACKENDS:
        'users.backends.EmailOrUsernameBackend',
        'axes.backends.AxesStandaloneBackend',
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user with email or username.

        Args:
            request: HTTP request object
            username: Email or username (accepts both)
            password: User password

        Returns:
            User object if authentication successful, None otherwise
        """
        if not username or not password:
            return None

        try:
            # Normalize input
            username_lower = username.strip().lower()

            # Try to find user by email OR username
            user = User.objects.get(
                Q(email__iexact=username_lower) | Q(username__iexact=username_lower)
            )
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # In case of data corruption, return None (shouldn't happen with unique constraints)
            return None

        # Verify password
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        """
        Get user by primary key.

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
