"""
CORS (Cross-Origin Resource Sharing) Configuration
For django-cors-headers package

Security-first CORS configuration with environment-specific settings.
Production uses explicit whitelist, development allows localhost origins.

References:
- https://github.com/adamchainz/django-cors-headers
- https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS
"""

import os

# Environment detection
IS_DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
IS_PRODUCTION = not IS_DEBUG

if IS_PRODUCTION:
    # Production CORS - Explicit whitelist only
    CORS_ALLOWED_ORIGINS = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        # Default to empty - MUST be configured in production
        "",
    ).split(",")

    # Remove empty strings from the list
    CORS_ALLOWED_ORIGINS = [
        origin.strip() for origin in CORS_ALLOWED_ORIGINS if origin.strip()
    ]

    # Example production origins (set via environment variable):
    # CORS_ALLOWED_ORIGINS=https://app.kinwise.com,https://www.kinwise.com,https://kinwise.app

    # Regex patterns for dynamic subdomains (optional)
    # CORS_ALLOWED_ORIGIN_REGEXES = [
    #     r"^https://\w+\.kinwise\.com$",  # Any subdomain of kinwise.com
    # ]

    CORS_ALLOW_ALL_ORIGINS = False

else:
    # Development CORS - Allow common local development origins
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:3000",  # React/Next.js dev server
        "http://localhost:3001",  # Alternative React port
        "http://localhost:4200",  # Angular dev server
        "http://localhost:8080",  # Vue.js dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:5173",
    ]

    # Can also use CORS_ALLOW_ALL_ORIGINS = True for maximum dev flexibility
    # CORS_ALLOW_ALL_ORIGINS = True  # Uncomment for wide-open dev CORS

# ==============================================================================
# CORS Security Settings (Apply to both dev and prod)
# ==============================================================================

# Allow cookies and authentication headers
CORS_ALLOW_CREDENTIALS = True

# Allowed HTTP methods
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]

# Allowed request headers
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# Headers exposed to browser
CORS_EXPOSE_HEADERS = [
    "content-type",
    "x-csrftoken",
]

# Preflight request cache duration (seconds)
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# ==============================================================================
# CORS URL Configuration (Optional)
# ==============================================================================

# Apply CORS only to specific URL patterns (if needed)
# CORS_URLS_REGEX = r'^/api/.*$'  # Only API endpoints

# Exempt specific URLs from CORS (if needed)
# CORS_EXEMPT_URLS = []

# ==============================================================================
# Production Security Recommendations
# ==============================================================================

"""
Production Checklist:

1. Set CORS_ALLOWED_ORIGINS environment variable:
   export CORS_ALLOWED_ORIGINS="https://app.kinwise.com,https://www.kinwise.com"

2. Never use CORS_ALLOW_ALL_ORIGINS = True in production

3. Use HTTPS origins only in production

4. Keep CORS_ALLOW_CREDENTIALS = True only if you need:
   - Cookie-based authentication
   - Session authentication
   - CSRF tokens

5. Minimize CORS_ALLOW_HEADERS to only what your frontend needs

6. Test CORS in production using:
   curl -H "Origin: https://app.kinwise.com" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS \
        https://api.kinwise.com/api/v1/transactions/

7. Monitor CORS errors in production logs

8. Consider using CORS_ALLOWED_ORIGIN_REGEXES for subdomain patterns
"""
