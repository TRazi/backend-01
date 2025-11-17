"""
KinWise API Client Example - Request Signing

This example shows how to implement request signing on the frontend
for secure communication with the KinWise API.

Usage:
    client = KinWiseAPIClient(base_url="http://localhost:8000", signing_key="your-key")
    response = client.post('/api/v1/transactions/', {'amount': 100})
"""

import hashlib
import hmac
import json
from typing import Optional, Dict, Any


class KinWiseAPIClient:
    """
    Secure API client with request signing support.
    
    Features:
    - Automatic HMAC-SHA256 request signing
    - JWT token authentication
    - Automatic retry on 401 (token refresh)
    - Request timeout handling
    - Request/response logging
    """
    
    def __init__(self, base_url: str, signing_key: Optional[str] = None, access_token: Optional[str] = None):
        """
        Initialize API client.
        
        Args:
            base_url: Base URL for API (e.g., 'http://localhost:8000')
            signing_key: Secret key for request signing (optional)
            access_token: JWT access token (optional)
        """
        self.base_url = base_url.rstrip('/')
        self.signing_key = signing_key
        self.access_token = access_token
        self.signing_enabled = signing_key is not None
    
    def _generate_signature(self, method: str, path: str, body: Optional[Dict] = None) -> str:
        """
        Generate HMAC-SHA256 signature for request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path (e.g., '/api/v1/transactions/')
            body: Request body (dict)
            
        Returns:
            Hexadecimal signature string
        """
        # Convert body to JSON string
        if body:
            body_str = json.dumps(body, separators=(',', ':'), sort_keys=True)
        else:
            body_str = ''
        
        # Hash body
        body_hash = hashlib.sha256(body_str.encode()).hexdigest()
        
        # Create message: METHOD:PATH:BODY_HASH
        message = f"{method}:{path}:{body_hash}"
        
        # Generate HMAC-SHA256
        signature = hmac.new(
            self.signing_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _build_headers(self, method: str, path: str, body: Optional[Dict] = None) -> Dict[str, str]:
        """
        Build request headers with authentication and signature.
        
        Args:
            method: HTTP method
            path: Request path
            body: Request body
            
        Returns:
            Dictionary of headers
        """
        headers = {
            'Content-Type': 'application/json',
        }
        
        # Add JWT token if available
        if self.access_token:
            headers['Authorization'] = f'Bearer {self.access_token}'
        
        # Add request signature if enabled
        if self.signing_enabled:
            signature = self._generate_signature(method, path, body)
            headers['X-Signature'] = signature
        
        return headers
    
    def post(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Make POST request with signed payload.
        
        Args:
            endpoint: API endpoint (e.g., '/api/v1/transactions/')
            data: Request body
            **kwargs: Additional requests arguments
            
        Returns:
            Response JSON
            
        Example:
            response = client.post('/api/v1/transactions/', {
                'amount': 100,
                'category': 'groceries',
                'date': '2025-11-17'
            })
        """
        # Note: In actual implementation, use requests library
        # This is pseudocode showing the pattern
        
        headers = self._build_headers('POST', endpoint, data)
        
        print(f"POST {endpoint}")
        print(f"Headers: {headers}")
        print(f"Body: {json.dumps(data)}")
        print(f"Signature: {headers.get('X-Signature')}")
        
        # In real implementation:
        # response = requests.post(
        #     f"{self.base_url}{endpoint}",
        #     json=data,
        #     headers=headers,
        #     timeout=30,
        #     **kwargs
        # )
        # return response.json()
    
    def put(self, endpoint: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Make PUT request with signed payload."""
        headers = self._build_headers('PUT', endpoint, data)
        # Implementation similar to post()
    
    def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make DELETE request with signature."""
        headers = self._build_headers('DELETE', endpoint)
        # Implementation similar to post()
    
    def get(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make GET request (no signature needed for safe methods)."""
        headers = self._build_headers('GET', endpoint)
        # Implementation similar to post()


# ==============================================================================
# JAVASCRIPT EXAMPLE
# ==============================================================================

JAVASCRIPT_EXAMPLE = """
// Frontend implementation using fetch API

class KinWiseAPIClient {
    constructor(baseUrl, signingKey, accessToken) {
        this.baseUrl = baseUrl;
        this.signingKey = signingKey;
        this.accessToken = accessToken;
        this.signingEnabled = signingKey !== null;
    }
    
    generateSignature(method, path, body = null) {
        // Create message: METHOD:PATH:BODY_HASH
        const bodyStr = body ? JSON.stringify(body) : '';
        const bodyHash = this.hashSha256(bodyStr);
        const message = `${method}:${path}:${bodyHash}`;
        
        // Generate HMAC-SHA256
        return this.hmacSha256(message, this.signingKey);
    }
    
    async hashSha256(data) {
        const msgBuffer = new TextEncoder().encode(data);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    
    async hmacSha256(message, key) {
        const msgBuffer = new TextEncoder().encode(message);
        const keyBuffer = new TextEncoder().encode(key);
        const cryptoKey = await crypto.subtle.importKey('raw', keyBuffer, 
            { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
        const signBuffer = await crypto.subtle.sign('HMAC', cryptoKey, msgBuffer);
        const signArray = Array.from(new Uint8Array(signBuffer));
        return signArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    
    async buildHeaders(method, path, body = null) {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.accessToken) {
            headers['Authorization'] = `Bearer ${this.accessToken}`;
        }
        
        if (this.signingEnabled) {
            const signature = await this.generateSignature(method, path, body);
            headers['X-Signature'] = signature;
        }
        
        return headers;
    }
    
    async post(endpoint, data) {
        const headers = await this.buildHeaders('POST', endpoint, data);
        
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(data),
            timeout: 30000,
        });
        
        return response.json();
    }
    
    async put(endpoint, data) {
        const headers = await this.buildHeaders('PUT', endpoint, data);
        // Similar implementation
    }
    
    async delete(endpoint) {
        const headers = await this.buildHeaders('DELETE', endpoint);
        // Similar implementation
    }
}

// Usage
const signingKey = 'your-signing-key'; // From server
const accessToken = 'jwt-token-here';
const client = new KinWiseAPIClient('http://localhost:8000', signingKey, accessToken);

// Make signed request
const response = await client.post('/api/v1/transactions/', {
    amount: 100,
    category: 'groceries',
    date: '2025-11-17'
});
"""


# ==============================================================================
# CURL EXAMPLE
# ==============================================================================

CURL_EXAMPLE = """
#!/bin/bash
# Example: Using curl with request signing

BASE_URL="http://localhost:8000"
SIGNING_KEY="your-signing-key"
ACCESS_TOKEN="your-jwt-token"
ENDPOINT="/api/v1/transactions/"
METHOD="POST"

# Request body
BODY='{"amount": 100, "category": "groceries"}'

# Calculate body hash
BODY_HASH=$(echo -n "$BODY" | sha256sum | cut -d' ' -f1)

# Create message to sign: METHOD:PATH:BODY_HASH
MESSAGE="$METHOD:$ENDPOINT:$BODY_HASH"

# Generate HMAC-SHA256 signature
SIGNATURE=$(echo -n "$MESSAGE" | openssl dgst -sha256 -hmac "$SIGNING_KEY" -r | cut -d' ' -f1)

# Make request
curl -X $METHOD \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $ACCESS_TOKEN" \\
  -H "X-Signature: $SIGNATURE" \\
  -d "$BODY" \\
  "$BASE_URL$ENDPOINT"
"""


# ==============================================================================
# TESTING
# ==============================================================================

def test_request_signing():
    """Test request signing implementation"""
    
    # Test case 1: POST transaction
    client = KinWiseAPIClient(
        base_url='http://localhost:8000',
        signing_key='test-key-12345',
        access_token='test-token'
    )
    
    path = '/api/v1/transactions/'
    body = {'amount': 100, 'category': 'groceries'}
    signature = client._generate_signature('POST', path, body)
    
    print(f"Test 1 - POST transaction")
    print(f"  Path: {path}")
    print(f"  Body: {body}")
    print(f"  Signature: {signature}")
    assert isinstance(signature, str), "Signature should be string"
    assert len(signature) == 64, "SHA256 should be 64 hex chars"
    print("  ✓ PASSED\n")
    
    # Test case 2: Different body should produce different signature
    body2 = {'amount': 200, 'category': 'utilities'}
    signature2 = client._generate_signature('POST', path, body2)
    
    print(f"Test 2 - Different body produces different signature")
    print(f"  Signature 1: {signature}")
    print(f"  Signature 2: {signature2}")
    assert signature != signature2, "Different bodies should produce different signatures"
    print("  ✓ PASSED\n")
    
    # Test case 3: Different method should produce different signature
    signature3 = client._generate_signature('PUT', path, body)
    
    print(f"Test 3 - Different method produces different signature")
    print(f"  POST Signature: {signature}")
    print(f"  PUT Signature:  {signature3}")
    assert signature != signature3, "Different methods should produce different signatures"
    print("  ✓ PASSED\n")
    
    print("All tests passed!")


if __name__ == '__main__':
    test_request_signing()
