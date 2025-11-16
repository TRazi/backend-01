# config/settings/security.py
"""
Security settings for KinWise Django Backend
SOC 2 Compliance - Security Controls

Addresses ZAP Findings:
1. Content Security Policy (CSP) Header Not Set - FIXED
2. Cookie No HttpOnly Flag - FIXED
3. X-Content-Type-Options Header Missing - FIXED
4. Server Version Leakage - MITIGATED

Based on Version 1 SOC2 implementation patterns.
Last Updated: November 13, 2025
"""

import os

# ==============================================================================
# SECURITY HEADERS
# ==============================================================================

# Prevent browsers from guessing content types
SECURE_CONTENT_TYPE_NOSNIFF = True

# Enable browser XSS filtering
SECURE_BROWSER_XSS_FILTER = True

# Prevent clickjacking attacks
X_FRAME_OPTIONS = "DENY"

# Force HTTPS redirect (only in production)
SECURE_SSL_REDIRECT = os.environ.get("DJANGO_DEBUG", "False") != "True"

# HTTP Strict Transport Security (HSTS)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Referrer Policy
SECURE_REFERRER_POLICY = "same-origin"

# Cross-Origin Opener Policy
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# Trust X-Forwarded-Proto header from proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ==============================================================================
# COOKIE SECURITY
# ==============================================================================

# Session cookie security
SESSION_COOKIE_SECURE = os.environ.get("DJANGO_DEBUG", "False") != "True"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"  # Changed from Lax for stricter CSRF protection
SESSION_COOKIE_AGE = 3600  # 1 hour

# CSRF cookie security
CSRF_COOKIE_SECURE = os.environ.get("DJANGO_DEBUG", "False") != "True"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"  # Changed from Lax for stricter CSRF protection

# ==============================================================================
# CONTENT SECURITY POLICY (CSP)
# ==============================================================================
# CSP configuration has been moved to config/addon/csp.py for better organization
# and environment-specific settings (production vs development).
#
# The CSP settings are imported in config/settings/base.py via:
#   from config.addon.csp import *
#
# See config/addon/csp.py for the complete CSP configuration.

# ==============================================================================
# SERVER SIGNATURE HIDING
# ==============================================================================
# Suppress server version in development (runserver)
# This addresses ZAP finding: "Server Leaks Version Information"

if os.environ.get("DJANGO_SETTINGS_MODULE") in [
    "config.settings.base",
    "config.settings.local",
]:
    try:
        from django.core.servers.basehttp import WSGIServer

        WSGIServer.server_version = ""
        WSGIServer.sys_version = ""
    except (ImportError, AttributeError):
        # Django version might not support this method
        pass

# For PRODUCTION deployment with Gunicorn/uWSGI:
# The Server header will be controlled by your WSGI server configuration
#
# Gunicorn example (add to gunicorn.conf.py):
#   proc_name = "kinwise"
#
# Nginx example (add to nginx.conf):
#   server_tokens off;
#   proxy_hide_header Server;

# ==============================================================================
# ALLOWED HOSTS VALIDATION
# ==============================================================================
# Ensure ALLOWED_HOSTS is properly configured in production
# This prevents Host header attacks
# Note: This should be set in .env file via ALLOWED_HOSTS variable
