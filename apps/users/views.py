"""
User Registration View

Django Best Practice: Use APIView for simple endpoints,
implement rate limiting for security, and audit logging.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from users.serializers import UserRegistrationSerializer
from audit.services import log_action


class UserRegistrationView(APIView):
    """
    User registration endpoint.
    Rate limited to 3 registrations per hour per IP.
    Public endpoint - no authentication required.
    """

    permission_classes = [AllowAny]

    @method_decorator(ratelimit(key="ip", rate="3/h", method="POST"))
    def post(self, request):
        """
        Register a new user.

        Request body:
        {
            "email": "user@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "first_name": "John",  // optional
            "last_name": "Doe"      // optional
        }

        Response:
        {
            "message": "Registration successful...",
            "email": "user@example.com",
            "user_id": 123
        }
        """
        serializer = UserRegistrationSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            # Log registration
            log_action(
                user=user,
                action_type="CREATE",
                action_description=f"User registered: {user.email}",
                request=request,
                object_type="User",
                object_id=user.id,
            )

            return Response(
                {
                    "message": "Registration successful. Please check your email to verify your account.",
                    "email": user.email,
                    "user_id": user.id,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
