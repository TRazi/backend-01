# Quick Reference: API Security Setup

## 5-Minute Setup

### Step 1: Generate Key
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 2: Update `.env`
```env
API_SIGNING_KEY=<paste_generated_key>
API_REQUEST_SIGNING_ENABLED=False
REQUEST_TIMEOUT_SECONDS=30
SLOW_REQUEST_THRESHOLD_SECONDS=10
MAX_REQUEST_SIZE_MB=10
```

### Step 3: Test
```bash
python manage.py test tests.test_api_security
```

### Step 4: Enable (Production Only)
```env
API_REQUEST_SIGNING_ENABLED=True
```

---

## What Each Security Feature Does

### 🛡️ Rate Limiting
- Blocks 6th failed login attempt within a minute
- Protects against brute force attacks

### 🔒 CORS
- Allows only whitelisted frontend domains
- Prevents unauthorized cross-origin requests

### 📦 API Versioning
- All endpoints use `/api/v1/`
- Allows multiple versions to coexist

### ✍️ Request Signing
- Signs financial transactions with HMAC-SHA256
- Prevents request tampering and forgery

### ⏱️ Request Timeouts
- Limits request execution time (default: 30s)
- Logs slow requests (default: > 10s)
- Enforces maximum request size (default: 10MB)

---

## Testing Request Signing

### Generate Signature
```python
from scripts.api_client_example import KinWiseAPIClient

client = KinWiseAPIClient(
    'http://localhost:8000',
    'your-signing-key',
    'your-token'
)

sig = client._generate_signature(
    'POST',
    '/api/v1/transactions/',
    {'amount': 100}
)
print(sig)  # 64-char hex string
```

### Send Signed Request
```bash
curl -X POST http://localhost:8000/api/v1/transactions/ \
    -H "Content-Type: application/json" \
    -H "X-Signature: $SIGNATURE" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"amount": 100}'
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Missing X-Signature header" | Add request signing to client |
| "Invalid signature" | Check signing key matches |
| Slow requests logged | Optimize database queries |
| "Payload Too Large" | Reduce request size or increase limit |

---

## Files Created

```
config/middleware/
  ├── request_signing.py        ← Verifies HMAC signatures
  └── request_timeout.py         ← Tracks duration & size

docs/
  ├── SECURITY_IMPLEMENTATION_GUIDE.md      ← Master guide
  ├── API_SECURITY_IMPLEMENTATION.md        ← API details
  └── API_SECURITY_IMPLEMENTATION_SUMMARY.md ← This phase

scripts/
  └── api_client_example.py      ← Client implementation examples

tests/
  └── test_api_security.py       ← Test suite
```

---

## Environment Variables

```env
# Request Signing
API_SIGNING_KEY=                          # 64-char hex from: python -c "import secrets; print(secrets.token_hex(32))"
API_REQUEST_SIGNING_ENABLED=False         # Set to True in production

# Timeouts
REQUEST_TIMEOUT_SECONDS=30                # Max execution time
SLOW_REQUEST_THRESHOLD_SECONDS=10         # Log if slower than this
MAX_REQUEST_SIZE_MB=10                    # Max request size in MB
MAX_JSON_BODY_SIZE=1048576                # Max JSON body in bytes
```

---

## Protected Endpoints

When `API_REQUEST_SIGNING_ENABLED=True`, these need signatures:

- `POST/PUT/DELETE /api/v1/transactions/`
- `POST/PUT/DELETE /api/v1/bills/`
- `POST/PUT/DELETE /api/v1/accounts/`
- `POST/PUT/DELETE /api/v1/households/`
- `POST/PUT /api/v1/transfers/`

---

## Deployment Checklist

- [ ] Generate new signing key for production
- [ ] Update `.env` with production key
- [ ] Set `API_REQUEST_SIGNING_ENABLED=True`
- [ ] Test all protected endpoints with signatures
- [ ] Brief frontend team on request signing
- [ ] Monitor logs for signature failures
- [ ] Set up alerts for timeout/size violations

---

## Key Files to Review

1. **Setup:** `docs/API_SECURITY_IMPLEMENTATION.md` → "Quick Start"
2. **Examples:** `scripts/api_client_example.py`
3. **Tests:** `tests/test_api_security.py`
4. **Reference:** `docs/SECURITY_IMPLEMENTATION_GUIDE.md` → "3. API Security"

---

**Status:** ✅ Complete  
**Last Updated:** November 17, 2025
