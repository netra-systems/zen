# Issue #1195 Auth SSOT Migration Examples

**Created:** 2025-09-15  
**Purpose:** Practical migration examples for converting JWT violations to SSOT auth helpers  
**Target Audience:** Developers implementing Issue #1195 remediation

## Migration Pattern Examples

### 1. Test File JWT Import Migration

**BEFORE (Violation):**
```python
import jwt
import pytest
from datetime import datetime, timedelta

class TestUserAuthentication:
    def test_token_validation(self):
        # Direct JWT encoding - VIOLATION
        token = jwt.encode({
            'user_id': 'test-user',
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'secret_key', algorithm='HS256')
        
        # Direct JWT decoding - VIOLATION  
        decoded = jwt.decode(token, 'secret_key', algorithms=['HS256'])
        assert decoded['user_id'] == 'test-user'
```

**AFTER (SSOT Compliant):**
```python
import pytest
from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper

class TestUserAuthentication:
    async def test_token_validation(self):
        # Use SSOT auth helper for token creation
        async with SSOTAuthTestHelper() as auth_helper:
            user_data = await auth_helper.create_test_user_with_token(
                email="test@example.com",
                permissions=["read", "write"]
            )
            token = user_data["access_token"]
            
            # Use SSOT auth helper for token validation
            validation = await auth_helper.validate_token_via_service(token)
            assert validation["valid"] is True
            assert validation["user_id"] == user_data["user_id"]
```

### 2. WebSocket Auth Test Migration

**BEFORE (Violation):**
```python
import jwt
import asyncio
from datetime import datetime, timedelta

class TestWebSocketAuth:
    def test_websocket_token_creation(self):
        # Direct JWT encoding for WebSocket - VIOLATION
        websocket_token = jwt.encode({
            'user_id': 'demo-user-001',
            'scopes': ['websocket', 'chat'],
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'websocket_secret', algorithm='HS256')
        
        return websocket_token
```

**AFTER (SSOT Compliant):**
```python
import asyncio
from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper

class TestWebSocketAuth:
    async def test_websocket_token_creation(self):
        # Use SSOT auth helper for WebSocket tokens
        async with SSOTAuthTestHelper() as auth_helper:
            user_data = await auth_helper.create_test_user_with_token(
                email="demo-user-001@example.com"
            )
            
            # Create WebSocket-specific token via auth service
            websocket_token = await auth_helper.create_websocket_auth_token(
                user_id=user_data["user_id"],
                scopes=['websocket', 'chat']
            )
            
            return websocket_token
```

### 3. Multi-User Isolation Testing

**BEFORE (Violation):**
```python
import jwt
from datetime import datetime, timedelta

class TestMultiUserIsolation:
    def create_user_tokens(self, user_count=3):
        tokens = []
        for i in range(user_count):
            # Direct JWT encoding - VIOLATION
            token = jwt.encode({
                'user_id': f'user-{i}',
                'exp': datetime.utcnow() + timedelta(hours=1)
            }, 'secret', algorithm='HS256')
            tokens.append(token)
        return tokens
```

**AFTER (SSOT Compliant):**
```python
from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper

class TestMultiUserIsolation:
    async def create_user_tokens(self, user_count=3):
        # Use SSOT auth helper for multi-user creation
        async with SSOTAuthTestHelper() as auth_helper:
            users = await auth_helper.create_multiple_test_users(
                count=user_count,
                email_prefix="test-user"
            )
            return [user["access_token"] for user in users]
```

### 4. Backend JWT Validation Migration

**BEFORE (Violation - Backend File):**
```python
# /netra_backend/app/core/unified/jwt_validator.py
import jwt
from typing import Dict, Any, Optional

class JWTValidator:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            # Direct JWT decoding in backend - VIOLATION
            decoded = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=['HS256']
            )
            return decoded
        except jwt.InvalidTokenError:
            return None
```

**AFTER (SSOT Compliant - Backend File):**
```python
# /netra_backend/app/core/unified/jwt_validator.py
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from typing import Dict, Any, Optional
import asyncio

class JWTValidator:
    def __init__(self):
        self.auth_client = AuthServiceClient()
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            # Delegate to auth service - SSOT COMPLIANT
            validation_result = await self.auth_client.validate_token(token)
            return validation_result if validation_result.get("valid") else None
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return None
    
    def validate_token_sync(self, token: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for backward compatibility."""
        return asyncio.run(self.validate_token(token))
```

### 5. WebSocket Core Auth Migration

**BEFORE (Violation - WebSocket Core):**
```python
# /netra_backend/app/websocket_core/__init__.py
import jwt
from typing import Optional, Dict, Any

async def validate_websocket_auth(token: str) -> Optional[Dict[str, Any]]:
    try:
        # Direct JWT operations in WebSocket core - VIOLATION
        decoded = jwt.decode(token, 'websocket_secret', algorithms=['HS256'])
        return decoded
    except jwt.InvalidTokenError:
        return None
```

**AFTER (SSOT Compliant - WebSocket Core):**
```python
# /netra_backend/app/websocket_core/__init__.py
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from typing import Optional, Dict, Any

async def validate_websocket_auth(token: str) -> Optional[Dict[str, Any]]:
    try:
        # Delegate to auth service - SSOT COMPLIANT
        auth_client = AuthServiceClient()
        validation_result = await auth_client.validate_token(token)
        
        # Additional WebSocket-specific validation if needed
        if validation_result.get("valid") and "websocket" in validation_result.get("permissions", []):
            return validation_result
        return None
    except Exception as e:
        logger.error(f"WebSocket token validation failed: {e}")
        return None
```

### 6. Auth Integration Pure Delegation

**BEFORE (Mixed - Auth Integration):**
```python
# /netra_backend/app/auth_integration/auth.py
import jwt
from netra_backend.app.clients.auth_client_core import AuthServiceClient

class AuthIntegration:
    def __init__(self):
        self.auth_client = AuthServiceClient()
        self.fallback_secret = "fallback_secret"
    
    async def validate_token(self, token: str):
        try:
            # Primary: Auth service validation
            result = await self.auth_client.validate_token(token)
            return result
        except Exception:
            # Fallback: Direct JWT validation - VIOLATION
            try:
                decoded = jwt.decode(token, self.fallback_secret, algorithms=['HS256'])
                return {"valid": True, "user_id": decoded["user_id"]}
            except:
                return {"valid": False}
```

**AFTER (Pure Delegation - SSOT Compliant):**
```python
# /netra_backend/app/auth_integration/auth.py
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)

class AuthIntegration:
    def __init__(self):
        self.auth_client = AuthServiceClient()
    
    async def validate_token(self, token: str):
        try:
            # Pure delegation to auth service - SSOT COMPLIANT
            result = await self.auth_client.validate_token(token)
            return result
        except Exception as e:
            logger.error(f"Auth service validation failed: {e}")
            # No fallback - maintain SSOT compliance
            return {"valid": False, "error": "Auth service unavailable"}
    
    async def create_token(self, user_id: str, permissions: list = None):
        # Pure delegation - SSOT COMPLIANT
        return await self.auth_client.generate_token(
            user_id=user_id,
            permissions=permissions or ["read", "write"]
        )
```

## Common Migration Patterns

### Pattern 1: Replace JWT Imports
```python
# BEFORE
import jwt

# AFTER  
from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper
```

### Pattern 2: Replace JWT Encoding
```python
# BEFORE
token = jwt.encode(payload, secret, algorithm='HS256')

# AFTER
async with SSOTAuthTestHelper() as auth_helper:
    user_data = await auth_helper.create_test_user_with_token(
        email=payload.get("email", "test@example.com"),
        permissions=payload.get("permissions", ["read", "write"])
    )
    token = user_data["access_token"]
```

### Pattern 3: Replace JWT Decoding
```python
# BEFORE
decoded = jwt.decode(token, secret, algorithms=['HS256'])

# AFTER
async with SSOTAuthTestHelper() as auth_helper:
    validation = await auth_helper.validate_token_via_service(token)
    decoded = validation if validation.get("valid") else None
```

### Pattern 4: Backend Auth Operations
```python
# BEFORE (in backend)
import jwt
result = jwt.decode(token, secret, algorithms=['HS256'])

# AFTER (in backend)
from netra_backend.app.clients.auth_client_core import AuthServiceClient
auth_client = AuthServiceClient()
result = await auth_client.validate_token(token)
```

## Migration Checklist

### For Each Test File:
- [ ] Remove `import jwt` statements
- [ ] Add `from test_framework.ssot.auth_test_helpers import SSOTAuthTestHelper`
- [ ] Replace `jwt.encode()` calls with `auth_helper.create_test_user_with_token()`
- [ ] Replace `jwt.decode()` calls with `auth_helper.validate_token_via_service()`
- [ ] Update test methods to be async if using auth helpers
- [ ] Add proper cleanup with async context manager

### For Each Backend File:
- [ ] Remove `import jwt` statements
- [ ] Add `from netra_backend.app.clients.auth_client_core import AuthServiceClient`
- [ ] Replace JWT operations with `auth_client.validate_token()` or `auth_client.generate_token()`
- [ ] Update methods to be async for auth service calls
- [ ] Remove any fallback JWT validation logic
- [ ] Add proper error handling for auth service calls

### For Auth Integration:
- [ ] Ensure pure delegation to AuthServiceClient
- [ ] Remove any local JWT operations
- [ ] Remove fallback mechanisms that bypass auth service
- [ ] Maintain error handling without compromising SSOT principles

## Testing the Migration

### Validation Steps:
1. **Run SSOT Compliance Tests:**
   ```bash
   python3 -m pytest tests/unit/auth_ssot/test_auth_ssot_compliance_validation.py -v
   ```

2. **Run Golden Path Tests:**
   ```bash
   python3 -m pytest tests/mission_critical/test_websocket_agent_events_suite.py -v
   ```

3. **Run Migrated Test Files:**
   ```bash
   python3 -m pytest path/to/migrated/test/file.py -v
   ```

### Expected Outcomes:
- SSOT compliance tests should show decreasing violation counts
- Golden Path functionality should remain fully operational
- Migrated tests should pass with auth service delegation
- No new auth SSOT violations should be introduced

## Troubleshooting Common Issues

### Issue: Async Context Problems
**Problem:** Test becomes async but test framework doesn't handle it
**Solution:** Use `@pytest.mark.asyncio` decorator or `asyncio.run()` wrapper

### Issue: Auth Service Unavailable in Tests
**Problem:** Auth service not running during test execution
**Solution:** Mock auth service responses or use test doubles in SSOT helpers

### Issue: Token Format Differences
**Problem:** Auth service tokens have different format than local JWT
**Solution:** Update assertions to use validation results rather than token content

### Issue: Performance in Test Suites
**Problem:** Auth service calls slow down test execution
**Solution:** Use auth helper caching and batch user creation

This migration guide provides the foundation for systematic remediation of all 303+ auth SSOT violations while maintaining Golden Path functionality and enterprise security compliance.