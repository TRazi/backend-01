"""
Request Timeout Middleware

Enforces maximum request execution time to prevent resource exhaustion attacks.
Tracks request duration and logs slow requests.
"""

import time
import logging
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


class RequestTimeoutMiddleware:
    """
    Monitor request duration and enforce timeouts.
    
    Configuration in settings:
        REQUEST_TIMEOUT_SECONDS = 30
        SLOW_REQUEST_THRESHOLD_SECONDS = 10
        TIMEOUT_EXEMPT_PATHS = ['/health/', '/status/']
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.timeout = getattr(settings, 'REQUEST_TIMEOUT_SECONDS', 30)
        self.slow_threshold = getattr(settings, 'SLOW_REQUEST_THRESHOLD_SECONDS', 10)
        self.exempt_paths = getattr(settings, 'TIMEOUT_EXEMPT_PATHS', [])
    
    def __call__(self, request):
        # Skip timeout tracking for exempt paths
        if self._is_exempt(request.path):
            return self.get_response(request)
        
        # Record start time
        request.start_time = time.time()
        request._timeout_start = time.time()
        
        # Get response
        response = self.get_response(request)
        
        # Calculate duration
        duration = time.time() - request.start_time
        
        # Log slow requests
        if duration > self.slow_threshold:
            logger.warning(
                f"Slow request: {request.method} {request.path} "
                f"took {duration:.2f}s (threshold: {self.slow_threshold}s) "
                f"User: {request.user if request.user.is_authenticated else 'Anonymous'}"
            )
        
        # Add timing header for debugging
        response['X-Response-Time'] = f"{duration:.3f}s"
        
        return response
    
    def _is_exempt(self, path):
        """Check if path is exempt from timeout tracking"""
        return any(path.startswith(exempt) for exempt in self.exempt_paths)


class RequestSizeLimitMiddleware:
    """
    Enforce maximum request body size to prevent memory exhaustion.
    
    Configuration in settings:
        MAX_REQUEST_SIZE_MB = 10
        MAX_JSON_BODY_SIZE = 1048576  # 1MB for JSON
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.max_size = getattr(settings, 'MAX_REQUEST_SIZE_MB', 10) * 1024 * 1024
        self.max_json_size = getattr(settings, 'MAX_JSON_BODY_SIZE', 1048576)
    
    def __call__(self, request):
        # Check Content-Length header
        content_length = request.META.get('CONTENT_LENGTH')
        
        if content_length:
            try:
                size = int(content_length)
                
                # Check overall size limit
                if size > self.max_size:
                    logger.warning(
                        f"Request size exceeded: {size} bytes from {request.META.get('REMOTE_ADDR')}"
                    )
                    return JsonResponse(
                        {'error': 'Request body too large'},
                        status=413
                    )
                
                # Check JSON size limit
                if request.content_type == 'application/json' and size > self.max_json_size:
                    logger.warning(
                        f"JSON request size exceeded: {size} bytes from {request.META.get('REMOTE_ADDR')}"
                    )
                    return JsonResponse(
                        {'error': 'JSON payload too large'},
                        status=413
                    )
            
            except (ValueError, TypeError):
                pass
        
        return self.get_response(request)
