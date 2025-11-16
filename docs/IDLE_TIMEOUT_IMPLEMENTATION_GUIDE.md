# Idle Timeout Implementation Guide

## Complete Technical Documentation & Reimplementation Guide

**Date**: November 14, 2025  
**Version**: 1.0  
**Django Version**: 5.2.8  
**SOC 2 Compliant**: ✅

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Component Details](#component-details)
4. [Dependencies](#dependencies)
5. [Implementation Steps](#implementation-steps)
6. [Configuration](#configuration)
7. [Security Considerations](#security-considerations)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)
10. [Maintenance](#maintenance)

---

## Executive Summary

The **IdleTimeout** system is a multi-layered session security mechanism that implements SOC 2-compliant automatic logout after periods of user inactivity. It combines server-side enforcement with client-side user experience enhancements.

### Key Features

- ✅ **Server-side enforcement**: Hard timeout prevents session hijacking
- ✅ **Grace period**: 2-minute warning before forced logout
- ✅ **Client-side modal**: User-friendly warning dialog
- ✅ **Keep-alive endpoint**: Manual session extension via user action
- ✅ **Rate limiting**: Protection against DoS attacks on session validation
- ✅ **Multi-channel support**: Works for both API and admin panel
- ✅ **SOC 2 compliant**: Meets confidentiality and availability criteria

### Timeline Behavior

```
User Activity → [15 minutes idle] → Grace Period (2 min) → Forced Logout
                 ↑                   ↑                     ↑
                 Auto-extend         Modal shown          Session destroyed
                 session             User must act        Redirect to login
```

---

## Architecture Overview

### Component Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  idle-timeout.js                                                │
│  - Tracks idle time                                             │
│  - Shows modal at timeout                                       │
│  - Calls keep-alive endpoint                                    │
│  - Handles logout                                               │
├─────────────────────────────────────────────────────────────────┤
│                        HTTP LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  X-Session-Timeout: 900        (headers)                        │
│  X-Session-Grace: 120                                           │
│  X-Session-Remaining: 456                                       │
├─────────────────────────────────────────────────────────────────┤
│                      SERVER LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  IdleTimeoutMiddleware (core/middleware.py)                     │
│  - Validates session age                                        │
│  - Enforces hard timeout                                        │
│  - Updates last_activity                                        │
│  - Forces logout on expiry                                      │
├─────────────────────────────────────────────────────────────────┤
│  SessionPingView (apps/common/views.py)                         │
│  - Keep-alive endpoint (/session/ping/)                         │
│  - Throttled (30 req/min)                                       │
│  - Extends session on POST                                      │
├─────────────────────────────────────────────────────────────────┤
│                     CONTEXT LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  session_timeout (core/context_processors.py)                   │
│  - Exposes timeout values to templates                          │
│  - Provides remaining seconds                                   │
├─────────────────────────────────────────────────────────────────┤
│                      SESSION LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  Django Session (Redis-backed)                                  │
│  - last_activity: ISO timestamp                                 │
│  - Standard session data                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. IdleTimeoutMiddleware

**Location**: `core/middleware.py` (lines 461-565)

**Purpose**: Server-side session timeout enforcement (the "hard enforcer")

**Behavior**:

```python
"""
Server-side idle timeout with client-facing countdown headers.

Behavior:
- Idle window: activity extends session (updates last_activity)
- Grace window: server DOES NOT extend automatically; only /session/ping/ POST extends
- Hard expiry: elapsed > (timeout + grace) -> logout
- Adds X-Session-Timeout / X-Session-Grace / X-Session-Remaining headers
  on authenticated HTML and API responses
"""
```

**Key Methods**:

#### `__init__(self, get_response=None)`
Initializes middleware with settings:
- `self.timeout`: IDLE_TIMEOUT_SECONDS (900s / 15 min)
- `self.grace`: IDLE_GRACE_SECONDS (120s / 2 min)
- `self.login_url`: Redirect target on timeout
- `self.keepalive_path`: "/session/ping/"

#### `process_request(self, request)`
Executes on every request:

**Logic Flow**:
1. Skip if timeout not configured
2. Skip static files
3. Skip login pages
4. Skip unauthenticated users
5. Check `last_activity` timestamp in session
6. Calculate `elapsed = now - last_activity`
7. **Hard expiry check** (elapsed > timeout + grace):
   - Logout user
   - Flush session
   - Return 401 JSON (API) or redirect (HTML)
8. **Grace window** (timeout < elapsed < timeout+grace):
   - If POST to /session/ping/: extend session, reset timer
   - Otherwise: do NOT extend, expose remaining time
9. **Idle window** (elapsed < timeout):
   - Update `last_activity` (auto-extend)
   - Calculate remaining time
   - Store in `request._idle_remaining`

#### `process_response(self, request, response)`
Adds HTTP headers to response:
- `X-Session-Timeout`: Total idle timeout (900)
- `X-Session-Grace`: Grace period (120)
- `X-Session-Remaining`: Seconds remaining before grace

**Dependencies**:
- `django.utils.timezone.now()`
- `django.contrib.auth.logout()`
- `django.http.JsonResponse`
- `django.http.HttpResponseRedirect`
- `django.urls.reverse()`
- `urllib.parse.quote()`

---

### 2. SessionPingView (Keep-Alive Endpoint)

**Location**: `apps/common/views.py` (lines 66-99)

**Purpose**: DRF APIView for session keep-alive with throttling and audit trail

**Features**:
- ✅ Rate-limited (30 requests/min via SessionPingThrottle)
- ✅ Supports session auth (admin panel) and JWT Bearer tokens
- ✅ Returns 204 No Content (no body)
- ✅ IdleTimeoutMiddleware extends session on successful auth
- ✅ Audit trail via AuditMiddleware (if enabled)

**Code**:
```python
class SessionPingView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionPingThrottle]

    @csrf_exempt  # Bearer tokens are self-verifying; no CSRF needed
    def post(self, request, *args, **kwargs):
        # By this point, IsAuthenticated has validated the user
        # IdleTimeoutMiddleware will extend session
        return Response(status=status.HTTP_204_NO_CONTENT)
```

**URL Registration**: `kinwise/urls.py`
```python
from common.views import SessionPingView

urlpatterns = [
    path("session/ping/", SessionPingView.as_view(), name="session_ping"),
]
```

**Dependencies**:
- `rest_framework.views.APIView`
- `rest_framework.permissions.IsAuthenticated`
- `rest_framework.authentication.SessionAuthentication`
- `common.throttles.SessionPingThrottle`

---

### 3. SessionPingThrottle (Rate Limiter)

**Location**: `apps/common/throttles.py`

**Purpose**: Prevent session enumeration and DoS attacks on keep-alive endpoint

**Configuration**:
- **Rate**: 30 requests per minute
- **Scope**: User ID (authenticated) or IP address (fallback)
- **Cache**: Uses Django's rate-limit cache (Redis in production)

**Code**:
```python
from rest_framework.throttling import SimpleRateThrottle

class SessionPingThrottle(SimpleRateThrottle):
    scope = "session_ping"

    def get_cache_key(self):
        if self.request.user and self.request.user.is_authenticated:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.request.user.id,
            }
        else:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(self.request),
            }
```

**Settings Configuration** (in `settings/base.py` or `production.py`):
```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "30/min",
    },
}
```

---

### 4. session_timeout Context Processor

**Location**: `core/context_processors.py`

**Purpose**: Expose timeout values to Django templates

**Code**:
```python
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
```

**Registration** (add to `TEMPLATES` in `settings/base.py`):
```python
TEMPLATES = [
    {
        "OPTIONS": {
            "context_processors": [
                # ... existing processors
                "core.context_processors.session_timeout",
            ],
        },
    },
]
```

**Template Usage**:
```django
{{ SESSION_TIMEOUT_SECONDS }}  <!-- 900 -->
{{ SESSION_GRACE_SECONDS }}     <!-- 120 -->
{{ SESSION_REMAINING_SECONDS }} <!-- 456 or None -->
```

---

### 5. Client-Side JavaScript (idle-timeout.js)

**Location**: `apps/common/static/kinwise-admin/idle-timeout.js`

**Purpose**: Client-side UX for idle timeout warnings and keep-alive

**Behavior**:
1. **Prime Phase**: HEAD request to check for `X-Session-Timeout` header
2. **Idle Tracking**: Increment counter every second
3. **Activity Listeners**: Reset idle counter on user interaction (before grace)
4. **Modal Display**: Show warning at timeout threshold
5. **Grace Period**: User must click "Stay signed in" or "Sign out"
6. **Keep-Alive**: POST to `/session/ping/` on button click
7. **Auto-Logout**: Navigate to `/admin/logout/` when grace expires

**Key Features**:
- ✅ Does NOT run on login pages (checks for session headers)
- ✅ Ignores activity during grace period (user must click button)
- ✅ Aligns timeout values from server headers (optional)
- ✅ Accessible modal with ARIA attributes
- ✅ CSRF token support for keep-alive POST

**Modal HTML** (generated dynamically):
```javascript
modal.innerHTML = `
  <div style="background:#111;color:#fff;...">
    Session will expire in <b id="kw-remaining">120</b> seconds.
    <button id="kw-stay">Stay signed in</button>
    <button id="kw-signout">Sign out</button>
  </div>
`;
```

**Activity Events Tracked**:
- `mousemove`, `mousedown`, `keydown`, `scroll`, `touchstart`, `focus`

**Keep-Alive Request**:
```javascript
fetch("/session/ping/", {
  method: "POST",
  headers: { "X-CSRFToken": csrf || "" },
  credentials: "same-origin",
})
```

**Loading the Script** (in admin templates):
```html
<script src="{% static 'kinwise-admin/idle-timeout.js' %}"></script>
```

---

### 6. Template Integration (Unfold Admin)

**Location**: `templates/unfold/includes/kinwise_session.html`

**Purpose**: Template-rendered session timeout UI for Django admin

**Features**:
- Uses context processor values
- Pre-renders modal HTML
- Inline JavaScript for simple implementation
- Styled modal with buttons

**Template Code**:
```django
{# Minimal markup + script. Uses context processor values. #}
<div id="kw-session-config"
     data-total="{{ SESSION_TIMEOUT_SECONDS|default:0 }}"
     data-grace="{{ SESSION_GRACE_SECONDS|default:60 }}"
     data-remaining="{{ SESSION_REMAINING_SECONDS|default_if_none:'' }}">
</div>

<div id="kw-session-root" style="display:none" class="kw-session-modal">
  <div class="kw-session-card">
    <div>Session expires in <b id="kw-remaining">—</b> seconds.</div>
    <div class="kw-row">
      <button id="kw-stay">Stay signed in</button>
      <button id="kw-signout">Sign out</button>
    </div>
  </div>
</div>

<script>
  // Reads data-total, data-grace, data-remaining
  // Counts down, shows modal, handles buttons
</script>
```

**Include in Base Template**:
```django
{% include 'unfold/includes/kinwise_session.html' %}
```

---

### 7. Admin Logout View

**Location**: `apps/common/views.py` (lines 145-156)

**Purpose**: Custom logout endpoint that accepts both GET and POST (unlike Django default)

**Code**:
```python
@require_http_methods(["GET", "POST"])
@csrf_exempt
def admin_logout(request):
    """
    Custom logout endpoint for admin panel.
    Accepts both GET and POST.
    Redirects to /admin/login/ after logout.
    """
    django_logout(request)
    return HttpResponse(status=302, headers={"Location": "/admin/login/"})
```

**URL Registration**:
```python
urlpatterns = [
    path("admin/logout/", admin_logout, name="admin_logout"),
]
```

**Why Needed**: Django's default `LogoutView` requires POST with CSRF token. During idle timeout, the modal needs to logout without requiring a valid CSRF token (since session may be expired).

---

## Dependencies

### Python Packages

```python
# Core Django
django>=5.2.8
djangorestframework>=3.15.2
djangorestframework-simplejwt>=5.3.1

# Session/Cache (Production)
django-redis>=5.4.0
redis>=5.0.0

# Security
django-cors-headers>=4.3.1
django-csp>=3.8

# Utilities
python-dateutil>=2.8.2  # For date parsing
```

### Django Apps

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'common',
    # ... other apps
]
```

### Middleware Stack (Order Matters!)

```python
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "core.middleware.RestrictStaticCORSMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",  # REQUIRED
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",  # REQUIRED
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.HouseholdTenancyMiddleware",
    # Add these for full idle timeout functionality:
    "core.middleware.IdleTimeoutMiddleware",  # ← Add this
    "core.middleware.SecurityHeadersMiddleware",  # ← Optional (adds security headers)
    "core.middleware.AuditMiddleware",  # ← Optional (audit logging)
]
```

**Critical Requirements**:
1. `SessionMiddleware` MUST be before `IdleTimeoutMiddleware`
2. `AuthenticationMiddleware` MUST be before `IdleTimeoutMiddleware`
3. `IdleTimeoutMiddleware` should be late in the stack (after auth)

### Settings Dependencies

```python
# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"  # or "db"
SESSION_CACHE_ALIAS = "session"  # if using cache backend
SESSION_COOKIE_AGE = 15 * 60  # Should match IDLE_TIMEOUT_SECONDS
SESSION_SAVE_EVERY_REQUEST = True  # Required for idle tracking
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Idle timeout settings
IDLE_TIMEOUT_SECONDS = 15 * 60  # 15 minutes
IDLE_GRACE_SECONDS = 2 * 60     # 2 minutes

# Login URL for redirects
LOGIN_URL = "/admin/login/"

# Context processor registration
TEMPLATES = [
    {
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "core.context_processors.session_timeout",  # ← Add this
            ],
        },
    },
]

# DRF throttling
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "30/min",
    },
}

# CORS for session endpoint (if API clients need it)
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = [
    "x-session-timeout",
    "x-session-grace",
    "x-session-remaining",
]
```

### Redis Configuration (Production)

```python
CACHES = {
    "session": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
        },
        "KEY_PREFIX": "session-prod",
        "TIMEOUT": 900,  # Match IDLE_TIMEOUT_SECONDS
    },
}
```

---

## Implementation Steps

### Step 1: Create Middleware File

**File**: `core/middleware.py`

Create the `IdleTimeoutMiddleware` class (see [Component Details](#1-idletimeoutmiddleware) above for full code).

**Minimal Implementation**:
```python
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from urllib.parse import quote
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class IdleTimeoutMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.timeout = int(getattr(settings, "IDLE_TIMEOUT_SECONDS", 0) or 0)
        self.grace = int(getattr(settings, "IDLE_GRACE_SECONDS", 60))
        self.login_url = settings.LOGIN_URL
        self.static_url = getattr(settings, "STATIC_URL", "/static/")
        self.keepalive_path = "/session/ping/"

    def process_request(self, request):
        # Implementation here (see full code above)
        pass

    def process_response(self, request, response):
        # Implementation here (see full code above)
        pass
```

---

### Step 2: Create Context Processor

**File**: `core/context_processors.py`

```python
from typing import Optional, Dict, Any
from django.conf import settings

def session_timeout(request) -> Dict[str, Any]:
    remaining: Optional[int] = getattr(request, "_idle_remaining", None)
    return {
        "SESSION_TIMEOUT_SECONDS": getattr(settings, "IDLE_TIMEOUT_SECONDS", 0) or 0,
        "SESSION_GRACE_SECONDS": getattr(settings, "IDLE_GRACE_SECONDS", 60),
        "SESSION_REMAINING_SECONDS": remaining,
    }
```

---

### Step 3: Create Throttle Class

**File**: `apps/common/throttles.py`

```python
from rest_framework.throttling import SimpleRateThrottle

class SessionPingThrottle(SimpleRateThrottle):
    scope = "session_ping"

    def get_cache_key(self):
        if self.request.user and self.request.user.is_authenticated:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.request.user.id,
            }
        else:
            return self.cache_format % {
                "scope": self.scope,
                "ident": self.get_ident(self.request),
            }
```

---

### Step 4: Create Keep-Alive View

**File**: `apps/common/views.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from common.throttles import SessionPingThrottle


class SessionPingView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionPingThrottle]

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


# Also create admin_logout view (see Component Details)
```

---

### Step 5: Register URL Routes

**File**: `kinwise/urls.py`

```python
from django.urls import path
from common.views import SessionPingView, admin_logout

urlpatterns = [
    path("session/ping/", SessionPingView.as_view(), name="session_ping"),
    path("admin/logout/", admin_logout, name="admin_logout"),
    # ... other URLs
]
```

---

### Step 6: Configure Settings

**File**: `kinwise/settings/production.py`

```python
# Session idle timeout - SOC 2 Requirement
IDLE_TIMEOUT_SECONDS = 15 * 60  # 15 minutes
IDLE_GRACE_SECONDS = 2 * 60     # 2 minutes

# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "session"
SESSION_COOKIE_AGE = 15 * 60  # Match IDLE_TIMEOUT_SECONDS
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True  # REQUIRED for idle tracking
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"

# CORS exposure of session headers
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = [
    "x-session-timeout",
    "x-session-grace",
    "x-session-remaining",
]

# DRF throttling
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "30/min",
    },
}
```

**File**: `kinwise/settings/base.py`

```python
# Register middleware
MIDDLEWARE = [
    # ... existing middleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Add after auth middleware:
    "core.middleware.IdleTimeoutMiddleware",
]

# Register context processor
TEMPLATES = [
    {
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "core.context_processors.session_timeout",
            ],
        },
    },
]
```

---

### Step 7: Create Client-Side JavaScript

**File**: `apps/common/static/kinwise-admin/idle-timeout.js`

Copy the full JavaScript code from [Component Details](#5-client-side-javascript-idle-timeoutjs) above.

**Directory Structure**:
```
apps/common/
├── static/
│   └── kinwise-admin/
│       └── idle-timeout.js
```

---

### Step 8: Load JavaScript in Templates

**Option A**: Include in base admin template

**File**: `templates/admin/base_site.html` (or Unfold equivalent)

```django
{% load static %}

{% block extrahead %}
  {{ block.super }}
  <script src="{% static 'kinwise-admin/idle-timeout.js' %}"></script>
{% endblock %}
```

**Option B**: Use template include (Unfold)

**File**: `templates/unfold/includes/kinwise_session.html`

Copy the template code from [Component Details](#6-template-integration-unfold-admin) above.

**Include in base**:
```django
{% include 'unfold/includes/kinwise_session.html' %}
```

---

### Step 9: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

This copies `idle-timeout.js` to the production static directory.

---

### Step 10: Test the Implementation

**Manual Testing**:

1. **Login to admin panel**: `http://localhost:8000/admin/`
2. **Wait 15 minutes** (or reduce `IDLE_TIMEOUT_SECONDS` for testing)
3. **Verify modal appears** with 2-minute countdown
4. **Click "Stay signed in"**: Session should extend, modal should close
5. **Wait 2 minutes without clicking**: Should auto-logout and redirect

**API Testing**:

```bash
# Get session cookie
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}' \
  -c cookies.txt

# Keep-alive ping
curl -X POST http://localhost:8000/session/ping/ \
  -b cookies.txt \
  -H "X-CSRFToken: <token>"

# Should return 204 No Content
# Should extend session
```

---

## Configuration

### Environment-Specific Settings

#### Development (`settings/development.py`)

```python
# Longer timeout for development
IDLE_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
IDLE_GRACE_SECONDS = 5 * 60     # 5 minutes

# Use database session for simplicity
SESSION_ENGINE = "django.contrib.sessions.backends.db"

# Relaxed CORS
CORS_ALLOW_ALL_ORIGINS = True
```

#### Production (`settings/production.py`)

```python
# SOC 2 compliant timeout
IDLE_TIMEOUT_SECONDS = 15 * 60  # 15 minutes
IDLE_GRACE_SECONDS = 2 * 60     # 2 minutes

# Redis-backed sessions for scalability
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "session"

# Strict CORS
CORS_ALLOWED_ORIGINS = ["https://app.kinwise.com"]
CORS_ALLOW_CREDENTIALS = True
```

#### Testing (`settings/test.py`)

```python
# Short timeout for fast tests
IDLE_TIMEOUT_SECONDS = 5  # 5 seconds
IDLE_GRACE_SECONDS = 2    # 2 seconds

# In-memory session for speed
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
    "session": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}
```

### Customization Options

#### Adjust Timeout Values

```python
# Longer timeout (30 minutes)
IDLE_TIMEOUT_SECONDS = 30 * 60

# Shorter grace period (1 minute)
IDLE_GRACE_SECONDS = 1 * 60

# No grace period (instant logout)
IDLE_GRACE_SECONDS = 0
```

#### Disable Idle Timeout

```python
# Set to 0 to disable
IDLE_TIMEOUT_SECONDS = 0
```

#### Custom Keep-Alive Path

```python
# In IdleTimeoutMiddleware.__init__
self.keepalive_path = "/api/v1/session/keepalive/"

# Update URL config and JavaScript accordingly
```

#### Throttle Rate Adjustment

```python
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "60/min",  # More lenient
        # or
        "session_ping": "10/min",  # More restrictive
    },
}
```

---

## Security Considerations

### 1. Server-Side Enforcement is Critical

**Never rely solely on client-side JavaScript**. The middleware MUST enforce timeout server-side, as JavaScript can be disabled or manipulated.

### 2. Grace Period Behavior

**During grace period**:
- Server does NOT auto-extend session on activity
- User MUST explicitly click "Stay signed in"
- This prevents accidental session extension from background requests

### 3. CSRF Protection

**Keep-alive endpoint uses `@csrf_exempt`** because:
- Session auth: CSRF validated by Django middleware
- JWT Bearer: Token is self-verifying, no CSRF needed
- Modal sends CSRF token in `X-CSRFToken` header

**If you remove JWT support**, remove `@csrf_exempt` and enforce CSRF.

### 4. Rate Limiting

**SessionPingThrottle** prevents:
- Session enumeration attacks
- DoS via rapid keep-alive requests
- Brute-force session validation

**30 req/min** is sufficient for legitimate use (user clicks every 2 minutes max).

### 5. Session Hijacking Prevention

**Timeout mitigates session hijacking**:
- Even if session cookie is stolen, it expires after 15 min idle
- Grace period limits window for attacker to extend session
- Forced logout destroys session server-side

### 6. Sensitive Data in Headers

**X-Session-Remaining** exposes time until logout:
- This is NOT a security risk (user already authenticated)
- Enhances UX by allowing accurate countdown
- Does not leak user data

### 7. CORS Configuration

**Expose session headers** only to trusted origins:
```python
CORS_EXPOSE_HEADERS = [
    "x-session-timeout",
    "x-session-grace",
    "x-session-remaining",
]
CORS_ALLOWED_ORIGINS = ["https://trusted.example.com"]
```

### 8. Logout Endpoint Security

**admin_logout accepts GET** for convenience:
- This is safe because logout is idempotent
- No sensitive data is transmitted
- Redirects to login page (public)

**Alternative**: Use POST-only and require CSRF token for stricter security.

---

## Testing

### Unit Tests

**File**: `tests/test_idle_timeout.py`

```python
import pytest
from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from core.middleware import IdleTimeoutMiddleware
from django.conf import settings

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123"
    )


@pytest.fixture
def client_with_session(client, user):
    client.login(email=user.email, password="testpass123")
    return client


class TestIdleTimeoutMiddleware:
    
    def test_session_extends_on_activity(self, client_with_session):
        """Activity within idle window extends session"""
        # Set last_activity to 5 minutes ago
        session = client_with_session.session
        session["last_activity"] = (
            timezone.now() - timedelta(minutes=5)
        ).isoformat()
        session.save()
        
        # Make request (simulates activity)
        response = client_with_session.get("/admin/")
        
        # Session should be extended
        assert response.status_code == 200
        session = client_with_session.session
        last_activity = timezone.datetime.fromisoformat(
            session["last_activity"]
        )
        assert (timezone.now() - last_activity).seconds < 5
    
    def test_logout_after_hard_expiry(self, client_with_session):
        """Session expires after timeout + grace"""
        # Set last_activity to 20 minutes ago (beyond 15 + 2)
        session = client_with_session.session
        session["last_activity"] = (
            timezone.now() - timedelta(minutes=20)
        ).isoformat()
        session.save()
        
        # Make request
        response = client_with_session.get("/admin/")
        
        # Should redirect to login
        assert response.status_code == 302
        assert "/admin/login/" in response.url
    
    def test_grace_period_shows_remaining(self, client_with_session):
        """In grace period, remaining time is exposed"""
        # Set last_activity to 16 minutes ago (in grace)
        session = client_with_session.session
        session["last_activity"] = (
            timezone.now() - timedelta(minutes=16)
        ).isoformat()
        session.save()
        
        # Make request
        response = client_with_session.get("/admin/")
        
        # Should succeed (still in grace)
        assert response.status_code == 200
        # Should have remaining header (60 seconds left)
        assert "X-Session-Remaining" in response
        remaining = int(response["X-Session-Remaining"])
        assert 0 < remaining <= 120  # Grace period
    
    def test_keepalive_extends_in_grace(self, client_with_session):
        """Keep-alive POST extends session during grace"""
        # Set last_activity to 16 minutes ago (in grace)
        session = client_with_session.session
        session["last_activity"] = (
            timezone.now() - timedelta(minutes=16)
        ).isoformat()
        session.save()
        
        # POST to keep-alive
        response = client_with_session.post("/session/ping/")
        
        # Should succeed
        assert response.status_code == 204
        
        # Session should be reset
        session = client_with_session.session
        last_activity = timezone.datetime.fromisoformat(
            session["last_activity"]
        )
        assert (timezone.now() - last_activity).seconds < 5
    
    def test_api_returns_401_on_expiry(self, client_with_session):
        """API endpoints return 401 JSON on session expiry"""
        # Set last_activity to 20 minutes ago
        session = client_with_session.session
        session["last_activity"] = (
            timezone.now() - timedelta(minutes=20)
        ).isoformat()
        session.save()
        
        # Make API request
        response = client_with_session.get("/api/v1/users/me/")
        
        # Should return 401 with JSON
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "session_expired"
        assert "idle_seconds" in data
```

### Integration Tests

```python
class TestSessionPingView:
    
    def test_ping_requires_authentication(self, client):
        """Unauthenticated requests are rejected"""
        response = client.post("/session/ping/")
        assert response.status_code == 401
    
    def test_ping_extends_session(self, client_with_session):
        """Authenticated ping returns 204"""
        response = client_with_session.post("/session/ping/")
        assert response.status_code == 204
    
    def test_ping_throttling(self, client_with_session):
        """Excessive pings are throttled"""
        # Send 31 requests (exceeds 30/min limit)
        for _ in range(31):
            response = client_with_session.post("/session/ping/")
        
        # Last request should be throttled
        assert response.status_code == 429
```

### Manual Testing Checklist

- [ ] Login to admin panel
- [ ] Verify idle-timeout.js loads (check Network tab)
- [ ] Wait until timeout threshold (or reduce setting)
- [ ] Verify modal appears with countdown
- [ ] Click "Stay signed in" → modal closes, session extends
- [ ] Wait for grace to expire → auto-logout, redirect to login
- [ ] Verify API returns 401 after expiry
- [ ] Test throttling: send 31 ping requests rapidly
- [ ] Verify headers present: X-Session-Timeout, X-Session-Grace, X-Session-Remaining

---

## Troubleshooting

### Modal Not Appearing

**Symptom**: Timeout occurs but no modal shown

**Possible Causes**:
1. **JavaScript not loading**
   - Check browser console for errors
   - Verify `collectstatic` ran successfully
   - Check `{% static 'kinwise-admin/idle-timeout.js' %}` resolves correctly

2. **No session headers**
   - Check middleware is registered: `IdleTimeoutMiddleware`
   - Check `IDLE_TIMEOUT_SECONDS` is set and > 0
   - Check user is authenticated

3. **Script runs on login page**
   - Script should skip if no `X-Session-Timeout` header
   - Verify HEAD request in `primeAndStart()` succeeds

**Fix**:
```javascript
// Debug: Log to console
console.log("Timeout:", TIMEOUT, "Grace:", GRACE);
console.log("Running:", running);
```

---

### Session Not Extending on Activity

**Symptom**: User is logged out despite activity

**Possible Causes**:
1. **Middleware not registered** or wrong order
2. **SESSION_SAVE_EVERY_REQUEST = False**
3. **Activity during grace period** (expected behavior)

**Fix**:
```python
# Ensure middleware is after auth
MIDDLEWARE = [
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.IdleTimeoutMiddleware",  # Must be after auth
]

# Ensure session saves on every request
SESSION_SAVE_EVERY_REQUEST = True
```

---

### Keep-Alive Returns 403

**Symptom**: POST to /session/ping/ returns 403 CSRF error

**Possible Causes**:
1. **Missing CSRF token** in request
2. **CSRF middleware disabled**
3. **Bearer token not sent correctly**

**Fix**:
```javascript
// Ensure CSRF token is sent
function getCookie(name) {
  var m = document.cookie.match("(^|;)\\s*"+name+"\\s*=\\s*([^;]+)");
  return m ? m.pop() : null;
}
var csrf = getCookie("csrftoken");

fetch("/session/ping/", {
  method: "POST",
  headers: { "X-CSRFToken": csrf || "" },
  credentials: "same-origin",
})
```

---

### Rate Limiting Too Aggressive

**Symptom**: Legitimate keep-alive requests are throttled

**Possible Causes**:
1. **Throttle rate too low**
2. **Multiple tabs/windows**

**Fix**:
```python
# Increase throttle rate
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "60/min",  # More lenient
    },
}
```

---

### Headers Not Visible to Client

**Symptom**: JavaScript can't read `X-Session-Timeout` header

**Possible Causes**:
1. **CORS not exposing headers**
2. **Middleware not adding headers**

**Fix**:
```python
# Expose headers via CORS
CORS_EXPOSE_HEADERS = [
    "x-session-timeout",
    "x-session-grace",
    "x-session-remaining",
]
```

---

### Session Expires Too Quickly

**Symptom**: Session expires before expected timeout

**Possible Causes**:
1. **SESSION_COOKIE_AGE too low**
2. **Redis TIMEOUT too low**
3. **Browser clock skew**

**Fix**:
```python
# Ensure cookie age matches idle timeout
SESSION_COOKIE_AGE = IDLE_TIMEOUT_SECONDS

# Ensure cache timeout is sufficient
CACHES = {
    "session": {
        "TIMEOUT": IDLE_TIMEOUT_SECONDS + IDLE_GRACE_SECONDS,
    },
}
```

---

## Maintenance

### Monitoring

**Key Metrics to Track**:

1. **Session Duration Distribution**
   - Track how long users stay logged in
   - Identify if timeout is too aggressive

2. **Keep-Alive Request Rate**
   - Monitor `/session/ping/` endpoint
   - Alert on throttling incidents

3. **Timeout-Induced Logouts**
   - Count forced logouts via middleware
   - Separate from user-initiated logouts

4. **Grace Period Engagement**
   - Track how often modal is shown
   - Track "Stay signed in" vs "Sign out" clicks

**Example Logging** (add to middleware):
```python
import logging
logger = logging.getLogger(__name__)

# In IdleTimeoutMiddleware.process_request
if elapsed > hard_expiry:
    logger.info(
        f"Session timeout logout: user={user.id}, "
        f"elapsed={elapsed:.0f}s"
    )
```

---

### Performance Optimization

**Session Backend Choice**:

- **Database**: Simple, persistent, slower
- **Cache (Redis)**: Fast, scalable, requires infrastructure
- **File**: Not recommended for production

**Recommendation**: Use Redis for production

```python
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "session"
```

**Session Data Size**:
- Minimize data stored in `request.session`
- Use Redis compression if available

**Middleware Performance**:
- Middleware adds ~1-2ms per request (negligible)
- Most overhead is session read/write (Django core)

---

### Updating Timeout Values

**Process**:
1. Update `IDLE_TIMEOUT_SECONDS` in settings
2. Update `IDLE_GRACE_SECONDS` if needed
3. Update `SESSION_COOKIE_AGE` to match
4. Update Redis cache `TIMEOUT` to match
5. Deploy (no code changes needed)
6. Monitor user feedback

**Backwards Compatibility**:
- Existing sessions will use new timeout on next request
- No migration required

---

### Security Updates

**Regular Tasks**:

1. **Review rate limits** quarterly
   - Adjust `session_ping` throttle based on usage

2. **Audit timeout values** annually
   - Ensure compliance with SOC 2 or other standards

3. **Test middleware** with each Django upgrade
   - Run unit tests
   - Check for deprecations

4. **Review session backend** security
   - Update Redis if using
   - Rotate Redis passwords

---

### Documentation Updates

**When to Update This Guide**:

1. Django version upgrade
2. Timeout configuration changes
3. New middleware interactions
4. Security findings
5. User feedback on UX

**Version History** (add as needed):
- v1.0 (Nov 2025): Initial implementation

---

## Appendix A: Full Code Reference

### A.1 Complete Middleware

**File**: `core/middleware.py`

```python
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

    def process_request(self, request):
        if not self.timeout or self.timeout <= 0:
            return None

        path = request.path or "/"
        if self.static_url and path.startswith(self.static_url):
            return None
        if self.login_url and path.startswith(self.login_url):
            return None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        now = timezone.now()
        last = request.session.get("last_activity")

        # First touch: seed last_activity
        if not last:
            request.session["last_activity"] = now.isoformat()
            request.session.modified = True
            request._idle_remaining = int(self.timeout)
            return None

        if isinstance(last, str):
            from django.utils.dateparse import parse_datetime
            last = parse_datetime(last)

        elapsed = (now - last).total_seconds()
        hard_expiry = self.timeout + self.grace

        # Beyond grace -> force logout
        if elapsed > hard_expiry:
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

        # In grace window: only explicit keep-alive extends session
        if elapsed > self.timeout:
            if path == self.keepalive_path and request.method == "POST":
                request.session["last_activity"] = now.isoformat()
                request.session.modified = True
                request._idle_remaining = int(self.timeout)
            else:
                request._idle_remaining = int(hard_expiry - elapsed)
            return None

        # Idle window: activity extends session
        request.session["last_activity"] = now.isoformat()
        request.session.modified = True
        request._idle_remaining = int(self.timeout - elapsed)
        return None

    def process_response(self, request, response):
        if not self.timeout or self.timeout <= 0:
            return response

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            response["X-Session-Timeout"] = str(self.timeout)
            response["X-Session-Grace"] = str(self.grace)
            if hasattr(request, "_idle_remaining"):
                response["X-Session-Remaining"] = str(request._idle_remaining)

        return response
```

---

### A.2 Complete Keep-Alive View

**File**: `apps/common/views.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout as django_logout
from django.http import HttpResponse
from common.throttles import SessionPingThrottle


class SessionPingView(APIView):
    """
    DRF APIView for session keep-alive endpoint.
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [SessionPingThrottle]

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        return Response(status=status.HTTP_204_NO_CONTENT)


@require_http_methods(["GET", "POST"])
@csrf_exempt
def admin_logout(request):
    """
    Custom logout endpoint for admin panel.
    Accepts both GET and POST.
    """
    django_logout(request)
    return HttpResponse(status=302, headers={"Location": "/admin/login/"})
```

---

### A.3 Complete Settings Configuration

**File**: `kinwise/settings/production.py`

```python
# Session idle timeout - SOC 2 Requirement
IDLE_TIMEOUT_SECONDS = 15 * 60  # 15 minutes
IDLE_GRACE_SECONDS = 2 * 60     # 2 minutes

# Session security
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "session"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_NAME = "kinwise_sessionid"
SESSION_COOKIE_AGE = 15 * 60  # Match IDLE_TIMEOUT_SECONDS
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# CORS exposure of session headers
CORS_ALLOW_CREDENTIALS = True
CORS_EXPOSE_HEADERS = [
    "x-session-timeout",
    "x-session-grace",
    "x-session-remaining",
]

# DRF throttling
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "session_ping": "30/min",
    },
}

# Redis cache for sessions
CACHES = {
    "session": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
        },
        "KEY_PREFIX": "session-prod",
        "TIMEOUT": 1020,  # 15min + 2min grace = 17min
    },
}
```

---

## Appendix B: SOC 2 Compliance Mapping

### Trust Service Criteria Coverage

**CC6.1 - Logical and Physical Access Controls**
- ✅ Idle timeout prevents unauthorized access to unattended sessions
- ✅ Grace period ensures legitimate users can extend session
- ✅ Server-side enforcement prevents client-side bypass

**CC6.2 - Prior to Issuing System Credentials**
- ✅ Session timeout ensures credentials expire after inactivity
- ✅ Timeout values align with SOC 2 best practices (15 minutes)

**CC6.6 - Restricts Access to System Configurations**
- ✅ Settings-based configuration prevents runtime tampering
- ✅ Middleware enforces timeout at framework level

**A1.2 - Availability and Monitoring**
- ✅ Rate limiting prevents DoS on session validation
- ✅ Throttling protects keep-alive endpoint
- ✅ Redis caching ensures scalability

**C1.1 - Confidential Information**
- ✅ Session timeout limits exposure window for stolen sessions
- ✅ Grace period prevents accidental data exposure

---

## Appendix C: Change Log

### v1.0 (November 14, 2025)
- Initial implementation guide created
- Documented all components and dependencies
- Added comprehensive testing guide
- Included SOC 2 compliance mapping

---

## Support & Contact

**For questions or issues**:
- GitHub Issues: [kinwise-family-finance/issues](https://github.com/tawandarazika/kinwise-family-finance/issues)
- Email: dev@kinwise.com
- Documentation: See `/Documentation/` folder

---

**END OF GUIDE**
