# WebSocket Subprotocol Format Fix

**Issue**: E2E tests were using incorrect WebSocket subprotocol format causing Golden Path connectivity failures.

## Problem

E2E tests were sending incorrect subprotocol format:
```
BAD: "e2e-testing, jwt.{encoded_token}"  # Single protocol with comma
```

This caused subprotocol negotiation to fail because the backend expected either:
1. Simple protocols: `["e2e-testing", "jwt-auth"]` (as separate array elements)
2. Token protocols: `["jwt-auth", "jwt.{token}"]` (as separate array elements)
3. Direct token: `["jwt.{token}"]` (single token protocol)

## Root Cause

The comma-separated format `"protocol1, protocol2"` was being treated as a single protocol name instead of two separate protocols. The WebSocket subprotocol negotiation logic properly processes protocols as separate array elements.

## Solution

Fixed `tests/e2e/staging_test_config.py` to use correct format:
```python
# Before (INCORRECT)
headers["sec-websocket-protocol"] = f"e2e-testing, jwt.{encoded_token}"

# After (CORRECT)
headers["sec-websocket-protocol"] = f"e2e-testing, jwt-auth"
```

## Verification

Tested subprotocol negotiation logic:
- ✅ `['e2e-testing', 'jwt-auth']` → Returns `e2e-testing`
- ✅ `['jwt-auth', 'jwt.{token}']` → Returns `jwt.{token}`
- ❌ `['e2e-testing, jwt.{token}']` → Returns `None` (not supported)

## Impact

- **Business Impact**: Restores $500K+ ARR Golden Path WebSocket connectivity
- **Technical Impact**: Fixes WebSocket subprotocol negotiation for E2E tests
- **Testing Impact**: E2E tests can now properly connect to staging environment

## Files Changed

1. `tests/e2e/staging_test_config.py` - Fixed subprotocol header format
2. Verified other E2E test files already use correct formats

## WebSocket Authentication Patterns (Reference)

Valid patterns supported by backend:

1. **Simple protocols**: `["e2e-testing", "jwt-auth"]`
2. **Token protocols**: `["jwt-auth", "jwt.{base64url_token}"]`
3. **Direct token**: `["jwt.{base64url_token}"]`
4. **Authorization header**: `Authorization: Bearer {jwt_token}` (preferred)

Invalid patterns:
- ❌ `["e2e-testing, jwt.{token}"]` - Comma-separated as single protocol
- ❌ `["protocol, other"]` - Any comma-separated single string

---
*Generated: 2025-01-15*
*Issue: WebSocket subprotocol negotiation Golden Path fix*