"""
WhiteNoise security headers utility.

Adds security headers to static files served by WhiteNoise middleware.
This addresses ZAP Report 3 findings for missing X-Content-Type-Options headers.
"""


def add_security_headers(headers, path, url):
    """
    Add security headers to static files.
    
    Called by WhiteNoise for each static file served.
    
    Args:
        headers: dict of HTTP headers to be sent with the file
        path: absolute path to the file being served
        url: URL path of the file being requested
    
    Returns:
        Modified headers dict with security headers added
    """
    # Prevent MIME type sniffing
    headers["X-Content-Type-Options"] = "nosniff"
    
    # Add Cache-Control for performance (1 year for hashed files)
    if url.startswith("/static/"):
        headers["Cache-Control"] = "public, max-age=31536000, immutable"
    
    return headers
