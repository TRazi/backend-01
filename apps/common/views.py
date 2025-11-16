"""
Common views for shared functionality across the application.

This module provides views that are used across multiple apps,
including session management and utility endpoints.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework import status
from django.views.decorators.http import require_POST
from django.contrib.auth import logout as django_logout
from django.http import HttpResponseRedirect
from common.throttles import SessionPingThrottle


class SessionPingView(APIView):
    """
    DRF APIView for session keep-alive endpoint.

    This endpoint allows authenticated users to extend their session during
    the grace period. It's rate-limited to prevent abuse.

    **Behavior:**
    - Requires authentication (session-based)
    - CSRF protection enforced for session auth
    - Rate limited to 30 requests/minute via SessionPingThrottle
    - Returns 204 No Content on success
    - IdleTimeoutMiddleware extends session on successful POST

    **Security:**
    - CSRF token required for session-based requests
    - Throttling prevents session enumeration attacks

    **Usage:**
    ```javascript
    fetch('/session/ping/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json'
        },
        credentials: 'same-origin'
    });
    ```
    """

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionPingThrottle]

    def post(self, request, *args, **kwargs):
        """
        Handle keep-alive POST request.

        By the time this method executes:
        1. User has been authenticated (IsAuthenticated permission)
        2. Request has passed CSRF verification (SessionAuthentication)
        3. Request has passed throttle check (SessionPingThrottle)
        4. IdleTimeoutMiddleware will extend session automatically

        No additional logic needed - just return success.
        """
        return Response(status=status.HTTP_204_NO_CONTENT)


@require_POST
def admin_logout(request):
    """
    Custom logout endpoint for admin panel.

    **Security:**
    - Requires POST method (prevents CSRF attacks)
    - Django CSRF middleware enforces token validation
    - Safe to use from forms with {% csrf_token %}

    **Behavior:**
    - Logs out the user via django.contrib.auth.logout()
    - Flushes the session
    - Redirects to /admin/login/

    **Usage:**
    ```html
    <form method="post" action="{% url 'admin_logout' %}">
        {% csrf_token %}
        <button type="submit">Logout</button>
    </form>
    ```

    Or from JavaScript:
    ```javascript
    fetch('/admin/logout/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        },
        credentials: 'same-origin'
    }).then(() => {
        window.location.href = '/admin/login/';
    });
    ```

    Args:
        request: HTTP request object

    Returns:
        HTTP 302 redirect to admin login page
    """
    django_logout(request)
    return HttpResponseRedirect("/admin/login/")
