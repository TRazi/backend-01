"""
Production-Grade Content Security Policy Configuration
Strict CSP for all routes; admin routes use @csp_update decorator for Unfold compatibility
"""

import os

IS_DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"

# CSP directive constants
CSP_SELF = "'self'"
CSP_NONE = "'none'"
CSP_UNSAFE_INLINE = "'unsafe-inline'"
CSP_UNSAFE_EVAL = "'unsafe-eval'"
CSP_DATA = "data:"

# Strict CSP for all routes (production and development)
# Admin routes are relaxed via decorator in config/views/admin_csp.py
CSP_DEFAULT_SRC = (CSP_SELF,)
CSP_SCRIPT_SRC = (CSP_SELF,)
CSP_STYLE_SRC = (CSP_SELF,)
CSP_IMG_SRC = (
    CSP_SELF,
    CSP_DATA,
)
CSP_FONT_SRC = (CSP_SELF,)
CSP_CONNECT_SRC = (CSP_SELF,)
CSP_FRAME_ANCESTORS = (CSP_NONE,)
CSP_BASE_URI = (CSP_SELF,)
CSP_FORM_ACTION = (CSP_SELF,)
CSP_OBJECT_SRC = (CSP_NONE,)
CSP_MANIFEST_SRC = (CSP_SELF,)

# Development: Relax CSP for easier debugging
if IS_DEBUG:
    CSP_SCRIPT_SRC = (
        CSP_SELF,
        CSP_UNSAFE_INLINE,
        CSP_UNSAFE_EVAL,
    )
    CSP_STYLE_SRC = (
        CSP_SELF,
        CSP_UNSAFE_INLINE,
    )
    CSP_CONNECT_SRC = (
        CSP_SELF,
        "ws:",
        "wss:",
    )
    CSP_FONT_SRC = (
        CSP_SELF,
        CSP_DATA,
    )

# Enable nonce support for inline scripts/styles
CSP_INCLUDE_NONCE_IN = (
    "script-src",
    "style-src",
)

# Don't exclude any URLs from CSP (admin handled via decorator)
CSP_EXCLUDE_URL_PREFIXES = ()

# AWS S3 support (if configured)
AWS_BUCKET = os.getenv("AWS_STORAGE_BUCKET_NAME")
if AWS_BUCKET:
    S3_URL = f"https://{AWS_BUCKET}.s3.amazonaws.com"
    CSP_IMG_SRC = CSP_IMG_SRC + (S3_URL,)
    CSP_STYLE_SRC = CSP_STYLE_SRC + (S3_URL,)
    CSP_SCRIPT_SRC = CSP_SCRIPT_SRC + (S3_URL,)
    CSP_FONT_SRC = CSP_FONT_SRC + (S3_URL,)
