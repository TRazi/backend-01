# config/context_processors.py
from typing import Optional, Dict, Any
from django.conf import settings


def session_timeout(request) -> Dict[str, Any]:
    """
    Expose idle-timeout values to templates.
    Relies on IdleTimeoutMiddleware setting request._idle_remaining.
    """
    remaining: Optional[int] = getattr(request, "_idle_remaining", None)
    return {
        "SESSION_TIMEOUT_SECONDS": getattr(settings, "IDLE_TIMEOUT_SECONDS", 0) or 0,
        "SESSION_GRACE_SECONDS": getattr(settings, "IDLE_GRACE_SECONDS", 60),
        "SESSION_REMAINING_SECONDS": remaining,  # may be None on first hit
    }
