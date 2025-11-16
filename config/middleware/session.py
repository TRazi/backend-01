# config/middleware/session.py
"""
Idle Timeout Middleware - SOC 2 Compliant Session Management

Server-side idle timeout with client-facing countdown headers.

Behavior:
- Idle window: activity extends session (updates last_activity)
- Grace window: server DOES NOT extend automatically; only /session/ping/ POST extends
- Hard expiry: elapsed > (timeout + grace) -> logout
- Adds X-Session-Timeout / X-Session-Grace / X-Session-Remaining headers
  on authenticated HTML and API responses
"""

from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import quote
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class IdleTimeoutMiddleware(MiddlewareMixin):
    """
    Server-side idle timeout with client-facing countdown headers.

    Behavior:
    - Idle window: activity extends session (updates last_activity)
    - Grace window: server DOES NOT extend automatically; only /session/ping/ POST extends
    - Hard expiry: elapsed > (timeout + grace) -> logout
    - Adds X-Session-Timeout / X-Session-Grace / X-Session-Remaining headers
      on authenticated HTML and API responses
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.timeout = int(getattr(settings, "IDLE_TIMEOUT_SECONDS", 0) or 0)
        self.grace = int(getattr(settings, "IDLE_GRACE_SECONDS", 60))
        self.login_url = settings.LOGIN_URL
        self.static_url = getattr(settings, "STATIC_URL", "/static/")
        self.keepalive_path = "/session/ping/"

    def _should_skip_timeout_check(self, request):
        """Check if request should skip timeout processing."""
        if not self.timeout or self.timeout <= 0:
            return True

        path = request.path or "/"
        if self.static_url and path.startswith(self.static_url):
            return True
        if self.login_url and path.startswith(self.login_url):
            return True

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return True

        return False

    def _reset_session_activity(self, request, now):
        """Reset session activity timestamp to now."""
        request.session["last_activity"] = now.isoformat()
        request.session.modified = True
        request._idle_remaining = int(self.timeout)

    def _parse_last_activity(self, last_activity_str):
        """Parse last activity timestamp, returning None if invalid."""
        from django.utils.dateparse import parse_datetime

        return parse_datetime(last_activity_str)

    def _handle_hard_expiry(self, request, path, elapsed):
        """Handle session hard expiry (logout user)."""
        logout(request)
        try:
            request.session.flush()
        except Exception:
            pass

        if path.startswith("/api/"):
            return JsonResponse(
                {
                    "error": "session_expired",
                    "message": "Session expired due to inactivity",
                    "idle_seconds": int(elapsed),
                },
                status=401,
            )

        next_param = quote(path)
        login_target = self.login_url or reverse("admin:login")
        return HttpResponseRedirect(f"{login_target}?next={next_param}")

    def _handle_grace_window(self, request, path, elapsed, hard_expiry):
        """Handle session in grace window (only keep-alive extends)."""
        if path == self.keepalive_path and request.method == "POST":
            now = timezone.now()
            self._reset_session_activity(request, now)
        else:
            # Do not extend; expose remaining until hard expiry
            request._idle_remaining = int(hard_expiry - elapsed)
        return None

    def process_request(self, request):
        if self._should_skip_timeout_check(request):
            return None

        now = timezone.now()
        last = request.session.get("last_activity")
        path = request.path or "/"

        # First touch: seed last_activity
        if not last:
            self._reset_session_activity(request, now)
            return None

        # Parse timestamp if string
        if isinstance(last, str):
            last = self._parse_last_activity(last)
            if not last:
                self._reset_session_activity(request, now)
                return None

        elapsed = (now - last).total_seconds()
        hard_expiry = self.timeout + self.grace

        # Beyond grace -> force logout
        if elapsed > hard_expiry:
            return self._handle_hard_expiry(request, path, elapsed)

        # In grace window: only explicit keep-alive extends session
        if elapsed > self.timeout:
            return self._handle_grace_window(request, path, elapsed, hard_expiry)

        # Idle window (not in grace): activity extends session
        request.session["last_activity"] = now.isoformat()
        request.session.modified = True
        request._idle_remaining = int(self.timeout - elapsed)
        return None

    def process_response(self, request, response):
        if not self.timeout or self.timeout <= 0:
            return response

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            # Expose headers for both HTML and API so the client can align
            response["X-Session-Timeout"] = str(self.timeout)
            response["X-Session-Grace"] = str(self.grace)
            if hasattr(request, "_idle_remaining"):
                response["X-Session-Remaining"] = str(request._idle_remaining)

        return response
