# API Security Implementation Guide

This guide covers the API security features implemented in KinWise, including rate limiting, CORS, API versioning, request signing, and request timeouts.

## Quick Start

### Generate Signing Key

```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Example output: a7f3b2c1d9e6f4a2b1c3d5e7f9a2b4c6d8e0f1a3b5c7d9e1f3a5b7c9d1e3f5
```

### Add to `.env`

```env
# API Security Settings
API_SIGNING_KEY=your-generated-key-here
API_REQUEST_SIGNING_ENABLED=False  # Set to True in production
REQUEST_TIMEOUT_SECONDS=30
SLOW_REQUEST_THRESHOLD_SECONDS=10
MAX_REQUEST_SIZE_MB=10
```

---

## 1. Rate Limiting (✅ Already Configured)

**Location:** `config/utils/ratelimit.py`, `config/addon/cache.py`

**What It Does:**
- Limits failed login attempts (5 per minute)
- Configurable Redis-based caching
- Prevents brute force attacks

**Current Configuration:**
```python
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "ratelimit"  # Redis cache
```

**Test Rate Limiting:**
```bash
# Make 5 failed login requests
for i in {1..5}; do
    curl -X POST http://localhost:8000/api/v1/auth/login/ \
        -H "Content-Type: application/json" \
        -d '{"username": "wrong", "password": "wrong"}'
done

# 6th request should return 429 Too Many Requests
```

---

## 2. CORS Configuration (✅ Already Configured)

**Location:** `config/addon/cors.py`

**What It Does:**
- Allows cross-origin requests from specified domains
- Enables credentials (cookies, auth headers)
- Restricts methods and headers

**Current Configuration:**
```python
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
```

**Development Setup (`.env`):**
```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000
```

**Production Setup (`.env`):**
```env
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**Test CORS:**
```bash
# From browser console (e.g., on http://localhost:3000)
fetch('http://localhost:8000/api/v1/transactions/', {
    method: 'GET',
    headers: {
        'Authorization': 'Bearer your-token'
    },
    credentials: 'include'
})
.then(r => r.json())
.then(d => console.log(d))
```

---

## 3. API Versioning (✅ Already Implemented)

**Location:** `config/api_v1_urls.py`, `config/urls.py`

**What It Does:**
- All endpoints use `/api/v1/` prefix
- Allows multiple API versions to run simultaneously
- Enables backward compatibility

**Current Endpoints:**
```
GET    /api/v1/transactions/
POST   /api/v1/transactions/
PUT    /api/v1/transactions/{id}/
DELETE /api/v1/transactions/{id}/
...
```

**Future Versioning (When Creating v2):**
```python
# urls.py
urlpatterns = [
    path("api/v1/", include("config.api_v1_urls")),
    path("api/v2/", include("config.api_v2_urls")),
]
```

**Test API Version:**
```bash
curl http://localhost:8000/api/v1/transactions/ \
    -H "Authorization: Bearer your-token"
```

---

## 4. Request Signing (⚠️ NEW - For Sensitive Operations)

**Location:** `config/middleware/request_signing.py`

**What It Does:**
- Verifies HMAC-SHA256 signature on sensitive API requests
- Prevents request tampering and forgery
- Protects financial transactions and account changes

**Protected Endpoints:**
- POST/PUT/DELETE `/api/v1/transactions/`
- POST/PUT/DELETE `/api/v1/bills/`
- POST/PUT/DELETE `/api/v1/accounts/`
- POST/PUT/DELETE `/api/v1/households/`
- POST/PUT `/api/v1/transfers/`

### How It Works

**Client Side (Frontend):**
```python
# 1. Create message: METHOD:PATH:BODY_HASH
# 2. Calculate HMAC-SHA256(message, signing_key)
# 3. Send signature in X-Signature header

import hashlib, hmac

method = 'POST'
path = '/api/v1/transactions/'
body = '{"amount": 100, "category": "groceries"}'

# Hash the body
body_hash = hashlib.sha256(body.encode()).hexdigest()

# Create message
message = f"{method}:{path}:{body_hash}"

# Sign with key
signature = hmac.new(
    'your-signing-key'.encode(),
    message.encode(),
    hashlib.sha256
).hexdigest()

# Send request
headers = {
    'X-Signature': signature,
    'Authorization': f'Bearer {token}'
}
```

**Server Side (Django):**
```python
# 1. Receive request with X-Signature header
# 2. Reconstruct message (METHOD:PATH:BODY_HASH)
# 3. Calculate expected signature
# 4. Compare with provided signature using constant-time comparison
```

### Enable Request Signing

**Step 1: Generate Key**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Output: a7f3b2c1d9e6f4a2b1c3d5e7f9a2b4c6d8e0f1a3b5c7d9e1f3a5b7c9d1e3f5
```

**Step 2: Add to `.env`**
```env
API_SIGNING_KEY=a7f3b2c1d9e6f4a2b1c3d5e7f9a2b4c6d8e0f1a3b5c7d9e1f3a5b7c9d1e3f5
API_REQUEST_SIGNING_ENABLED=False  # Start with False for development
```

**Step 3: Share Key with Frontend Team**
```
⚠️ IMPORTANT: This key must be:
✓ Securely transmitted to frontend developers (not via email/Slack)
✓ Stored securely on frontend (environment variables, not hardcoded)
✓ NOT committed to version control
✓ Rotated periodically (e.g., quarterly)
✓ Different per environment (dev, staging, production)
```

**Step 4: Test Request Signing**
```bash
# Use provided script
python scripts/api_client_example.py

# Or use curl with request signing example
bash scripts/test_request_signing.sh
```

**Step 5: Enable in Production**
```env
API_REQUEST_SIGNING_ENABLED=True
```

### Request Signing Example (Python)

```python
from scripts.api_client_example import KinWiseAPIClient

# Initialize client
client = KinWiseAPIClient(
    base_url='http://localhost:8000',
    signing_key='your-signing-key',
    access_token='your-jwt-token'
)

# Make signed request (automatically signs)
response = client.post('/api/v1/transactions/', {
    'amount': 100,
    'category': 'groceries',
    'date': '2025-11-17'
})
```

### Request Signing Example (JavaScript)

```javascript
// See scripts/api_client_example.py for full JavaScript example

const client = new KinWiseAPIClient(
    'http://localhost:8000',
    'your-signing-key',
    'your-jwt-token'
);

// Make signed request
const response = await client.post('/api/v1/transactions/', {
    amount: 100,
    category: 'groceries',
    date: '2025-11-17'
});

console.log(response);
```

### Disable Request Signing for Specific Tests

```python
# For unit/integration tests that bypass middleware
from unittest.mock import patch

@patch.dict(os.environ, {'API_REQUEST_SIGNING_ENABLED': 'False'})
def test_transaction_creation():
    # Test without signatures
    response = client.post('/api/v1/transactions/', {...})
```

---

## 5. Request Timeout Limits (⚠️ NEW)

**Location:** `config/middleware/request_timeout.py`

**What It Does:**
- Enforces maximum request execution time (prevents resource exhaustion)
- Tracks request duration for performance monitoring
- Logs slow requests (> 10 seconds)
- Enforces request body size limits

### Configuration

**`.env` Settings:**
```env
REQUEST_TIMEOUT_SECONDS=30        # Max 30 seconds per request
SLOW_REQUEST_THRESHOLD_SECONDS=10 # Log if > 10 seconds
MAX_REQUEST_SIZE_MB=10             # Max 10MB total request size
MAX_JSON_BODY_SIZE=1048576        # Max 1MB for JSON payloads
```

### How It Works

**Request Timeout Middleware:**
1. Records request start time
2. Processes request normally
3. Calculates duration
4. Logs if duration exceeds threshold
5. Adds `X-Response-Time` header to response

**Request Size Limit Middleware:**
1. Reads Content-Length header
2. Rejects requests > MAX_REQUEST_SIZE_MB
3. Rejects JSON payloads > MAX_JSON_BODY_SIZE
4. Returns HTTP 413 (Payload Too Large) if exceeded

### Monitoring Request Times

**In Logs:**
```
WARNING - Slow request: GET /api/v1/transactions/ took 12.45s (threshold: 10s) User: user@example.com
```

**In Response Headers:**
```
X-Response-Time: 0.245s
```

**Test Timeout:**
```bash
# This should work (< 30s)
time curl http://localhost:8000/api/v1/transactions/ \
    -H "Authorization: Bearer your-token"

# Monitor performance
tail -f /var/log/kinwise/django.log | grep "Slow request"
```

**Test Size Limit:**
```bash
# Create 15MB file
dd if=/dev/zero bs=1M count=15 | base64 > large_file.txt

# Try to upload (should fail with 413)
curl -X POST http://localhost:8000/api/v1/transactions/1/upload_receipt/ \
    -H "Authorization: Bearer your-token" \
    -F "file=@large_file.txt"

# Response: {"error": "Request body too large"}
```

### Exempt Paths (No Timeout)

Health check and status endpoints are exempt:
```python
TIMEOUT_EXEMPT_PATHS = [
    "/health/",
    "/status/",
    "/api/v1/auth/login/",  # Auth may be slower
]
```

---

## Integration Testing

### Test Suite

Run comprehensive API security tests:

```bash
# Run all tests
python manage.py test tests/

# Run specific security tests
python manage.py test tests/api_security_tests.py

# Test rate limiting
python manage.py test tests/test_rate_limiting.py

# Test CORS
python manage.py test tests/test_cors.py

# Test request signing
python manage.py test tests/test_request_signing.py

# Test timeouts
python manage.py test tests/test_request_timeout.py
```

### Manual Testing (Development)

**1. Test Unsigned Request (Should Fail)**
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-token" \
    -d '{"amount": 100}'

# Response: {"error": "Missing X-Signature header"}
```

**2. Test with Invalid Signature (Should Fail)**
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-token" \
    -H "X-Signature: invalid_signature_here" \
    -d '{"amount": 100}'

# Response: {"error": "Invalid signature"}
```

**3. Test with Valid Signature (Should Succeed)**
```bash
python -c "
from scripts.api_client_example import KinWiseAPIClient
import json

client = KinWiseAPIClient(
    'http://localhost:8000',
    'your-signing-key',
    'your-token'
)

# Get signature
sig = client._generate_signature('POST', '/api/v1/transactions/', {'amount': 100})
print(f'Signature: {sig}')
"

# Use the signature in curl
curl -X POST http://localhost:8000/api/v1/transactions/ \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer your-token" \
    -H "X-Signature: [signature-from-above]" \
    -d '{"amount": 100}'
```

---

## Production Deployment Checklist

- [ ] Generate new signing key for production
- [ ] Store API_SIGNING_KEY in secure location (AWS Secrets Manager)
- [ ] Set API_REQUEST_SIGNING_ENABLED=True
- [ ] Update frontend to use request signing
- [ ] Test request signing with production key
- [ ] Monitor request timeout metrics
- [ ] Set appropriate timeout values for production workload
- [ ] Configure log aggregation for slow requests
- [ ] Set up alerts for signature verification failures
- [ ] Document process for rotating signing keys
- [ ] Communicate signing key securely to frontend team

---

## Troubleshooting

### Request Signing Failures

**Problem:** "Missing X-Signature header"
- **Cause:** Client not sending signature
- **Solution:** Implement request signing on client side

**Problem:** "Invalid signature"
- **Cause:** Signature calculation mismatch
- **Solution:** 
  1. Verify signing key matches on both sides
  2. Check message format (METHOD:PATH:BODY_HASH)
  3. Ensure body is properly JSON-serialized

**Problem:** Signature valid sometimes, invalid other times
- **Cause:** Non-deterministic JSON serialization
- **Solution:** Use `separators=(',', ':')` and `sort_keys=True` when serializing

### Timeout Issues

**Problem:** "Slow request" warnings
- **Cause:** Endpoint takes too long
- **Solution:**
  1. Optimize database queries
  2. Add indexes to frequently queried fields
  3. Implement caching
  4. Increase SLOW_REQUEST_THRESHOLD_SECONDS if necessary

**Problem:** "Payload Too Large" errors
- **Cause:** Request body exceeds limit
- **Solution:**
  1. Break large requests into smaller chunks
  2. Increase MAX_JSON_BODY_SIZE if appropriate
  3. Implement chunked file uploads

---

## Security Best Practices

✅ **DO:**
- Rotate signing key quarterly
- Monitor signature verification failures
- Log all failed signature attempts
- Use HTTPS in production (not HTTP)
- Store signing key securely
- Use different keys per environment

❌ **DON'T:**
- Commit signing key to version control
- Send signing key via email/Slack
- Reuse signing key across environments
- Log signing keys or signatures
- Disable request signing in production

---

## Performance Optimization

### Cache Signature Verification

For high-traffic scenarios, cache verification results:
```python
from django.core.cache import cache

CACHE_KEY = f"signature_valid:{request.path}:{signature}"
if cache.get(CACHE_KEY):
    # Signature already verified
    pass
else:
    if self._verify_signature(request, signature, body):
        cache.set(CACHE_KEY, True, 60)  # Cache for 60 seconds
```

### Batch Operations

Instead of multiple signed requests:
```python
# ❌ Not recommended: 10 requests = 10 signatures
for transaction in transactions:
    client.post('/api/v1/transactions/', transaction)

# ✅ Recommended: 1 request = 1 signature
client.post('/api/v1/transactions/batch/', {'transactions': transactions})
```

---

## References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/latest/)
- [Django Security Documentation](https://docs.djangoproject.com/en/5.2/topics/security/)
- [HMAC-SHA256 Specification](https://tools.ietf.org/html/rfc4868)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

**Last Updated:** November 17, 2025
**Status:** Production Ready
**Next Review:** December 17, 2025
