"""
Custom CSP Middleware - Route-Specific Security
Applies strict CSP to API routes, relaxed CSP to admin routes for Unfold compatibility
"""

import os

# CSP directive constants
CSP_SELF = "'self'"
CSP_NONE = "'none'"
CSP_UNSAFE_INLINE = "'unsafe-inline'"
CSP_UNSAFE_EVAL = "'unsafe-eval'"
CSP_DATA = "data:"

# AWS S3 URL for static/media files
AWS_BUCKET = os.getenv("AWS_S3_BUCKET_NAME") or os.getenv("AWS_STORAGE_BUCKET_NAME")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
if AWS_BUCKET:
    # Use regional S3 URL format: https://bucket.s3-region.amazonaws.com
    S3_URL = f"https://{AWS_BUCKET}.s3-{AWS_REGION}.amazonaws.com"
    # Also allow non-regional format as fallback
    S3_URL_ALT = f"https://{AWS_BUCKET}.s3.amazonaws.com"
else:
    S3_URL = None
    S3_URL_ALT = None


class CustomCSPMiddleware:
    """
    Custom Content Security Policy middleware with route-specific policies.

    - Admin routes (/admin/*): Relaxed CSP for Django Unfold compatibility
    - API routes (/api/*): Strict CSP with NO unsafe-inline/unsafe-eval
    - Other routes: Strict CSP
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.is_debug = os.getenv("DJANGO_DEBUG", "false").lower() == "true"

    def __call__(self, request):
        response = self.get_response(request)

        # Determine if this is an admin route
        is_admin_route = request.path.startswith("/admin/")

        # Build CSP header based on route
        if is_admin_route:
            # Admin CSP - Relaxed for Unfold (allows inline scripts/styles)
            style_src = [CSP_SELF, CSP_UNSAFE_INLINE, "https://fonts.googleapis.com"]
            script_src = [CSP_SELF, CSP_UNSAFE_INLINE, CSP_UNSAFE_EVAL]
            font_src = [CSP_SELF, CSP_DATA, "https://fonts.gstatic.com"]
            img_src = [CSP_SELF, CSP_DATA]
            
            # Add S3 URLs if configured
            if S3_URL:
                style_src.extend([S3_URL, S3_URL_ALT])
                script_src.extend([S3_URL, S3_URL_ALT])
                font_src.extend([S3_URL, S3_URL_ALT])
                img_src.extend([S3_URL, S3_URL_ALT])
            
            csp_directives = {
                "default-src": [CSP_SELF],
                "script-src": script_src,
                "style-src": style_src,
                "img-src": img_src,
                "font-src": font_src,
                "connect-src": (
                    [CSP_SELF, "ws:", "wss:"] if self.is_debug else [CSP_SELF]
                ),
                "frame-ancestors": [CSP_NONE],
                "base-uri": [CSP_SELF],
                "form-action": [CSP_SELF],
                "object-src": [CSP_NONE],
                "manifest-src": [CSP_SELF],
            }
        else:
            # API/Public CSP - Strict (NO unsafe-inline, NO unsafe-eval)
            style_src = [CSP_SELF]
            script_src = [CSP_SELF]
            font_src = [CSP_SELF]
            img_src = [CSP_SELF, CSP_DATA]
            
            # Add S3 URLs if configured
            if S3_URL:
                style_src.extend([S3_URL, S3_URL_ALT])
                script_src.extend([S3_URL, S3_URL_ALT])
                font_src.extend([S3_URL, S3_URL_ALT])
                img_src.extend([S3_URL, S3_URL_ALT])
            
            csp_directives = {
                "default-src": [CSP_SELF],
                "script-src": script_src,
                "style-src": style_src,
                "img-src": img_src,
                "font-src": font_src,
                "connect-src": (
                    [CSP_SELF, "ws:", "wss:"] if self.is_debug else [CSP_SELF]
                ),
                "frame-ancestors": [CSP_NONE],
                "base-uri": [CSP_SELF],
                "form-action": [CSP_SELF],
                "object-src": [CSP_NONE],
                "manifest-src": [CSP_SELF],
            }

        # Convert directives to CSP header string
        csp_parts = []
        for directive, values in csp_directives.items():
            csp_parts.append(f"{directive} {' '.join(values)}")

        csp_header = "; ".join(csp_parts)

        # Set the CSP header
        response["Content-Security-Policy"] = csp_header

        # Set X-Content-Type-Options to prevent MIME sniffing
        response["X-Content-Type-Options"] = "nosniff"

        return response
