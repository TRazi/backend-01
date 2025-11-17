"""
Request Signing Middleware for API Security

Verifies HMAC-SHA256 signatures on sensitive API requests to prevent tampering.
Ensures request authenticity and integrity.

Usage:
    Add to MIDDLEWARE in settings:
    'config.middleware.request_signing.RequestSigningMiddleware'
    
    Client sends requests with X-Signature header:
    headers = {
        'X-Signature': hmac_sha256(method:path:body, signing_key),
        'Authorization': 'Bearer token'
    }
"""

import hmac
import hashlib
import logging
from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import sync_and_async_middleware

logger = logging.getLogger(__name__)


@sync_and_async_middleware
class RequestSigningMiddleware:
    """
    Verify HMAC-SHA256 signatures on sensitive API endpoints.
    
    Protected endpoints:
    - POST/PUT/DELETE /api/v1/transactions/
    - POST/PUT/DELETE /api/v1/bills/
    - POST/PUT/DELETE /api/v1/accounts/
    - POST/PUT /api/v1/households/*/link-account/
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.signing_key = getattr(settings, 'API_SIGNING_KEY', None)
        self.enabled = getattr(settings, 'API_REQUEST_SIGNING_ENABLED', False)
        
        # Endpoints that require signature verification
        self.protected_paths = [
            '/api/v1/transactions/',
            '/api/v1/bills/',
            '/api/v1/accounts/',
            '/api/v1/households/',
            '/api/v1/transfers/',
        ]
        
        # Methods that require signatures
        self.protected_methods = ['POST', 'PUT', 'PATCH', 'DELETE']
    
    def __call__(self, request):
        # Skip signature verification if disabled or key not configured
        if not self.enabled or not self.signing_key:
            return self.get_response(request)
        
        # Check if this is a protected endpoint
        if self._is_protected_endpoint(request):
            signature = request.headers.get('X-Signature')
            
            if not signature:
                logger.warning(
                    f"Missing signature for {request.method} {request.path} "
                    f"from {request.META.get('REMOTE_ADDR')}"
                )
                return JsonResponse(
                    {'error': 'Missing X-Signature header'},
                    status=400
                )
            
            # Read request body for signature verification
            try:
                request_body = request.body.decode('utf-8') if request.body else ''
            except (UnicodeDecodeError, AttributeError):
                request_body = ''
            
            # Verify signature
            if not self._verify_signature(request, signature, request_body):
                logger.warning(
                    f"Invalid signature for {request.method} {request.path} "
                    f"from {request.META.get('REMOTE_ADDR')} "
                    f"User: {request.user}"
                )
                return JsonResponse(
                    {'error': 'Invalid signature'},
                    status=400
                )
            
            logger.debug(f"Valid signature for {request.method} {request.path}")
        
        return self.get_response(request)
    
    def _is_protected_endpoint(self, request):
        """Check if endpoint requires signature verification"""
        # Only verify mutations (POST, PUT, PATCH, DELETE)
        if request.method not in self.protected_methods:
            return False
        
        # Check if path matches protected paths
        path = request.path
        return any(path.startswith(protected) for protected in self.protected_paths)
    
    def _verify_signature(self, request, provided_signature, body):
        """
        Verify HMAC-SHA256 signature of the request.
        
        Args:
            request: HTTP request object
            provided_signature: Signature from X-Signature header (hex string)
            body: Request body content
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        try:
            # Reconstruct message that was signed
            # Format: METHOD:PATH:BODY_HASH
            # Using body hash instead of full body for performance
            body_hash = hashlib.sha256(body.encode() if isinstance(body, str) else body).hexdigest()
            message = f"{request.method}:{request.path}:{body_hash}"
            
            # Calculate expected signature
            expected_signature = hmac.new(
                self.signing_key.encode() if isinstance(self.signing_key, str) else self.signing_key,
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures using constant-time comparison
            # This prevents timing attacks
            return hmac.compare_digest(provided_signature, expected_signature)
        
        except Exception as e:
            logger.error(f"Error verifying signature: {str(e)}")
            return False


class RequestSigningUtility:
    """Utility class for generating signatures on the client side"""
    
    @staticmethod
    def generate_signature(method, path, body, signing_key):
        """
        Generate HMAC-SHA256 signature for a request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            body: Request body (dict or JSON string)
            signing_key: Secret signing key
            
        Returns:
            str: Hexadecimal signature
            
        Example:
            signature = RequestSigningUtility.generate_signature(
                method='POST',
                path='/api/v1/transactions/',
                body={'amount': 100, 'category': 'groceries'},
                signing_key='your-secret-key'
            )
            
            headers = {
                'X-Signature': signature,
                'Authorization': 'Bearer token'
            }
        """
        import json
        
        # Convert body to JSON string if it's a dict
        if isinstance(body, dict):
            body_str = json.dumps(body, separators=(',', ':'), sort_keys=True)
        else:
            body_str = body if body else ''
        
        # Hash body for efficiency
        body_hash = hashlib.sha256(body_str.encode()).hexdigest()
        
        # Create message: METHOD:PATH:BODY_HASH
        message = f"{method}:{path}:{body_hash}"
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            signing_key.encode() if isinstance(signing_key, str) else signing_key,
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def get_setup_instructions():
        """Get setup instructions for developers"""
        return """
# API Request Signing Setup

## 1. Generate Signing Key
python -c "import secrets; print(secrets.token_hex(32))"

## 2. Add to .env
API_SIGNING_KEY=<generated_key>
API_REQUEST_SIGNING_ENABLED=True

## 3. Frontend: Sign Requests

import hashlib
import hmac
import json

def sign_request(method, path, body, signing_key):
    '''Generate HMAC-SHA256 signature'''
    body_str = json.dumps(body) if body else ''
    body_hash = hashlib.sha256(body_str.encode()).hexdigest()
    message = f"{method}:{path}:{body_hash}"
    signature = hmac.new(
        signing_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature

# Usage
body = {'amount': 100, 'category': 'groceries'}
signature = sign_request('POST', '/api/v1/transactions/', body, API_SIGNING_KEY)

response = requests.post(
    'http://localhost:8000/api/v1/transactions/',
    headers={
        'X-Signature': signature,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    json=body
)
"""
