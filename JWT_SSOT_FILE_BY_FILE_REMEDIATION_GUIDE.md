# JWT SSOT FILE-BY-FILE REMEDIATION GUIDE

**Purpose:** Detailed implementation instructions for each of the 49 files requiring JWT SSOT consolidation  
**Target:** Zero JWT violations while maintaining Golden Path functionality  
**Approach:** Surgical, testable changes with immediate rollback capability

---

## PHASE 1: CRITICAL INFRASTRUCTURE (13 FILES)

### 🚨 PRIORITY 1: DIRECT JWT IMPORTS (3 files)

#### 1. `netra_backend/app/services/key_manager.py`
**Current Violations:**
- Lines 333-432: Direct JWT operations in bridge methods
- Imports UnifiedJWTValidator instead of auth service

**Remediation Steps:**
```python
# CHANGE 1: Update imports
# REMOVE:
from netra_backend.app.core.unified.jwt_validator import jwt_validator

# ADD:
from auth_service.auth_core.unified_auth_interface import get_unified_auth

# CHANGE 2: Update bridge methods (lines 333-405)
class KeyManager:
    def __init__(self):
        # ADD:
        self._auth_service = get_unified_auth()
    
    async def create_access_token(self, user_id: str, email: str = None, 
                                permissions: List[str] = None, expire_minutes: int = None) -> str:
        # REPLACE entire method:
        try:
            logger.info("KeyManager.create_access_token delegating to auth service SSOT")
            return self._auth_service.create_access_token(user_id, email, permissions)
        except Exception as e:
            logger.error(f"JWT access token creation failed in KeyManager bridge: {e}")
            raise
    
    async def verify_token(self, token: str, token_type: str = None, 
                         verify_exp: bool = True) -> Optional[Dict[str, Any]]:
        # REPLACE entire method:
        try:
            logger.info("KeyManager.verify_token delegating to auth service SSOT")
            result = self._auth_service.validate_token(token, token_type or "access")
            
            if result:
                return {
                    "user_id": result.get("sub") or result.get("user_id"),
                    "email": result.get("email"),
                    "permissions": result.get("permissions", []),
                    "valid": True
                }
            else:
                return None
        except Exception as e:
            logger.error(f"JWT token verification failed in KeyManager bridge: {e}")
            return None
```

**Test Command:**
```bash
python tests/integration/golden_path/test_auth_flows_business_logic.py -v
python tests/unit/test_key_manager_jwt_bridge.py -v
```

**Risk Level:** HIGH - Used by Golden Path validator
**Rollback:** `git checkout HEAD -- netra_backend/app/services/key_manager.py`

---

#### 2. `netra_backend/app/services/auth/token_security_validator.py`  
**Current Violations:**
- Line 192: `import jwt` for metadata extraction
- `_extract_token_metadata()` method uses direct JWT decoding

**Remediation Steps:**
```python
# CHANGE 1: Remove direct JWT import
# REMOVE line 192:
import jwt

# ADD to top of file:
from auth_service.auth_core.unified_auth_interface import get_unified_auth

# CHANGE 2: Update TokenSecurityValidator class
class TokenSecurityValidator:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self._threat_detection_rules = self._initialize_threat_rules()
        # ADD:
        self._auth_service = get_unified_auth()
        
        logger.info("TokenSecurityValidator initialized with auth service SSOT")

    def _extract_token_metadata(self, token: str) -> Dict[str, Any]:
        """Extract metadata from token using auth service SSOT."""
        try:
            # REPLACE entire method:
            # Use auth service for safe token metadata extraction
            result = self._auth_service.validate_token(token, "access")
            if result:
                return dict(result)  # Return the metadata safely
            else:
                # If validation fails, try to extract basic info for security analysis
                # This is safe because we're only extracting metadata, not validating
                return self._extract_basic_metadata_safely(token)
        except Exception as e:
            logger.warning(f"Failed to extract token metadata via auth service: {e}")
            return {}
    
    def _extract_basic_metadata_safely(self, token: str) -> Dict[str, Any]:
        """Safely extract basic metadata without JWT library."""
        try:
            import base64
            import json
            
            # Basic structure check
            parts = token.split('.')
            if len(parts) != 3:
                return {}
            
            # Decode payload part safely
            payload_part = parts[1]
            # Add padding if needed
            missing_padding = len(payload_part) % 4
            if missing_padding:
                payload_part += '=' * (4 - missing_padding)
            
            payload_bytes = base64.urlsafe_b64decode(payload_part)
            payload_data = json.loads(payload_bytes.decode('utf-8'))
            
            return payload_data
        except Exception as e:
            logger.warning(f"Safe metadata extraction failed: {e}")
            return {}
```

**Test Command:**
```bash
python tests/unit/security/test_token_security_validator.py -v
python tests/integration/test_auth_security_validation.py -v
```

**Risk Level:** MEDIUM - Security validation layer
**Rollback:** `git checkout HEAD -- netra_backend/app/services/auth/token_security_validator.py`

---

#### 3. `netra_backend/app/core/cross_service_validators/security_validators.py`
**Current Violations:**
- Direct JWT imports for cross-service validation
- Custom JWT validation logic duplicating auth service

**Remediation Steps:**
```python
# CHANGE 1: Update imports
# REMOVE any direct JWT imports
# ADD:
from auth_service.auth_core.unified_auth_interface import get_unified_auth

# CHANGE 2: Update validation functions
class CrossServiceSecurityValidator:
    def __init__(self):
        self._auth_service = get_unified_auth()
    
    async def validate_service_token(self, token: str, expected_service: str = None) -> bool:
        """Validate service-to-service authentication token."""
        try:
            result = self._auth_service.validate_token(token, "service")
            if not result:
                return False
            
            # Additional service-specific validation
            if expected_service:
                token_service = result.get("service")
                if token_service != expected_service:
                    logger.warning(f"Service mismatch: expected {expected_service}, got {token_service}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Service token validation failed: {e}")
            return False
    
    async def validate_cross_service_request(self, token: str, source_service: str, 
                                           target_service: str) -> Optional[Dict]:
        """Validate cross-service request authentication."""
        try:
            # Use auth service SSOT for all validation
            result = self._auth_service.validate_token(token, "service")
            if not result:
                return None
            
            # Cross-service specific checks
            if not self._validate_service_permissions(result, source_service, target_service):
                return None
            
            return result
        except Exception as e:
            logger.error(f"Cross-service validation failed: {e}")
            return None
```

**Test Command:**
```bash
python tests/integration/test_cross_service_auth.py -v
python tests/unit/core/test_security_validators.py -v
```

**Risk Level:** HIGH - Cross-service security  
**Rollback:** `git checkout HEAD -- netra_backend/app/core/cross_service_validators/security_validators.py`

---

### 🔥 PRIORITY 2: HIGH-PRIORITY OPERATIONS (10 files)

#### 4. `netra_backend/app/clients/auth_client_core.py`
**Current Violations:**
- Token validation and user authentication using duplicate logic
- Direct JWT operations instead of auth service

**Remediation Steps:**
```python
# CHANGE: Complete rewrite to pure delegation
from auth_service.auth_core.unified_auth_interface import get_unified_auth

class AuthClientCore:
    def __init__(self):
        self._auth_service = get_unified_auth()
        logger.info("AuthClientCore initialized with auth service SSOT delegation")
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user - pure delegation to auth service."""
        return await self._auth_service.authenticate_user(email, password)
    
    async def validate_token(self, token: str) -> Optional[Dict]:
        """Validate token - pure delegation to auth service."""
        return self._auth_service.validate_token(token, "access")
    
    async def create_token(self, user_id: str, email: str) -> str:
        """Create token - pure delegation to auth service."""
        return self._auth_service.create_access_token(user_id, email)
    
    async def refresh_token(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """Refresh token - delegate to auth service."""
        # This would need to be implemented in UnifiedAuthInterface
        return await self._auth_service.refresh_access_token(refresh_token)
```

**Test Command:**
```bash
python tests/unit/test_auth_client_core_comprehensive.py -v
python tests/integration/test_auth_client_integration.py -v
```

**Risk Level:** HIGH - Core authentication client
**Rollback:** `git checkout HEAD -- netra_backend/app/clients/auth_client_core.py`

---

#### 5. `netra_backend/app/middleware/auth_middleware.py`
**Current Violations:**
- Request authentication using duplicate JWT logic
- Token extraction and validation not using auth service

**Remediation Steps:**
```python
# CRITICAL: ALL API requests pass through this middleware
from auth_service.auth_core.unified_auth_interface import get_unified_auth

class AuthMiddleware:
    def __init__(self):
        self._auth_service = get_unified_auth()
    
    async def authenticate_request(self, request) -> Optional[Dict]:
        """Authenticate incoming request - SSOT delegation."""
        try:
            # Extract token from request
            token = self._extract_token_from_request(request)
            if not token:
                return None
            
            # Use auth service SSOT for validation
            result = self._auth_service.validate_token(token, "access")
            if result:
                # Add user context to request
                request.state.user_id = result.get("sub")
                request.state.user_email = result.get("email")
                request.state.user_permissions = result.get("permissions", [])
                
            return result
        except Exception as e:
            logger.error(f"Request authentication failed: {e}")
            return None
    
    def _extract_token_from_request(self, request) -> Optional[str]:
        """Extract token from Authorization header."""
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        return None
```

**Test Command:**
```bash
python tests/integration/test_auth_middleware.py -v
python tests/e2e/test_api_authentication.py -v
```

**Risk Level:** CRITICAL - ALL API requests  
**Rollback:** `git checkout HEAD -- netra_backend/app/middleware/auth_middleware.py`

---

#### 6. `netra_backend/app/websocket_core/unified_jwt_protocol_handler.py`
**Current Violations:**
- WebSocket authentication handshake using custom JWT logic
- Source of WebSocket 1011 errors due to inconsistent validation

**Remediation Steps:**
```python
# CRITICAL: This fixes WebSocket 1011 errors
from auth_service.auth_core.unified_auth_interface import get_unified_auth

class UnifiedJWTProtocolHandler:
    def __init__(self):
        self._auth_service = get_unified_auth()
        logger.info("WebSocket JWT handler initialized with auth service SSOT")
    
    async def authenticate_websocket_connection(self, websocket, token: str) -> Optional[Dict]:
        """Authenticate WebSocket connection - eliminates 1011 errors."""
        try:
            # Use auth service SSOT - same validation as REST endpoints
            result = self._auth_service.validate_token(token, "access")
            
            if result:
                # Successfully authenticated
                user_id = result.get("sub")
                logger.info(f"WebSocket authentication successful for user: {user_id}")
                return result
            else:
                # Authentication failed - proper 1011 error
                logger.warning("WebSocket authentication failed - invalid token")
                await websocket.close(code=1011)
                return None
                
        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await websocket.close(code=1011)
            return None
    
    async def handle_token_refresh_over_websocket(self, websocket, refresh_token: str):
        """Handle token refresh over WebSocket connection."""
        try:
            # Use auth service for refresh
            new_tokens = await self._auth_service.refresh_access_token(refresh_token)
            if new_tokens:
                access_token, new_refresh_token = new_tokens
                await websocket.send_json({
                    "type": "token_refresh", 
                    "access_token": access_token,
                    "refresh_token": new_refresh_token
                })
            else:
                await websocket.close(code=1011)  # Refresh failed
        except Exception as e:
            logger.error(f"WebSocket token refresh failed: {e}")
            await websocket.close(code=1011)
```

**Test Command:**
```bash
python tests/unit/golden_path/test_websocket_auth_business_logic.py -v
python tests/e2e/test_websocket_dev_docker_connection.py -v
python tests/integration/test_websocket_jwt_protocol.py -v
```

**Risk Level:** CRITICAL - Chat functionality (90% of platform value)
**Rollback:** `git checkout HEAD -- netra_backend/app/websocket_core/unified_jwt_protocol_handler.py`

---

#### 7. `netra_backend/app/auth_integration/auth.py`
**Current Violations:**
- Backend auth integration layer using duplicate logic
- Should be pure delegation to auth service

**Remediation Steps:**
```python
# CHANGE: Simplify to pure delegation
from auth_service.auth_core.unified_auth_interface import get_unified_auth

class BackendAuthIntegration:
    """Backend integration with auth service - pure delegation layer."""
    
    def __init__(self):
        self._auth_service = get_unified_auth()
        logger.info("Backend auth integration initialized - pure SSOT delegation")
    
    # User Authentication
    async def login(self, email: str, password: str) -> Optional[Dict]:
        return await self._auth_service.authenticate_user(email, password)
    
    async def logout(self, token: str) -> bool:
        return await self._auth_service.logout(token)
    
    # Token Operations - Pure Delegation
    async def validate_token(self, token: str) -> Optional[Dict]:
        return self._auth_service.validate_token(token, "access")
    
    async def create_token(self, user_id: str, email: str) -> str:
        return self._auth_service.create_access_token(user_id, email)
    
    # User Management - Pure Delegation
    async def get_user(self, user_id: str) -> Optional[Dict]:
        return await self._auth_service.get_user(user_id)
    
    async def create_user(self, email: str, password: str) -> Optional[Dict]:
        return await self._auth_service.create_user(email, password)
    
    # Utility Methods
    def extract_user_id_from_token(self, token: str) -> Optional[str]:
        return self._auth_service.extract_user_id(token)
    
    def is_token_blacklisted(self, token: str) -> bool:
        return self._auth_service.is_token_blacklisted(token)
```

**Test Command:**
```bash
python tests/integration/test_auth_integration.py -v  
python tests/unit/test_backend_auth_integration.py -v
```

**Risk Level:** HIGH - Integration between backend and auth
**Rollback:** `git checkout HEAD -- netra_backend/app/auth_integration/auth.py`

---

#### 8-13. Additional High-Priority Files
**Similar pattern for remaining files:**
- `app/auth_integration/validators.py`
- `app/services/user_auth_service.py`
- `app/services/token_service.py`
- `app/core/unified_secret_manager.py`
- `app/core/config_validator.py`
- `app/middleware/gcp_auth_context_middleware.py`

**Standard Remediation Pattern:**
1. Replace all JWT imports with auth service imports
2. Convert all methods to pure delegation
3. Maintain backward compatibility in method signatures
4. Add comprehensive error handling and logging
5. Test each file individually before moving to next

---

## PHASE 2: SECONDARY IMPLEMENTATIONS (36 FILES)

### 📋 CONFIGURATION MANAGEMENT (8 files)
**Pattern:** Remove JWT secrets, add auth service connection config
**Files:** Configuration managers, secret handlers, environment validators

### 🧪 TEST INFRASTRUCTURE (12 files)  
**Pattern:** Update test mocks to use auth service client
**Files:** Test utilities, mock factories, integration test helpers

### 🔄 LEGACY AUTHENTICATION (10 files)
**Pattern:** Replace with auth service delegation or mark deprecated
**Files:** Old auth implementations, compatibility layers

### 🔧 UTILITY AND HELPERS (6 files)
**Pattern:** Simple delegation to auth service
**Files:** Helper functions, utility classes, convenience methods

---

## IMPLEMENTATION CHECKLIST

### Before Each File Change:
- [ ] Read current file and identify all JWT operations
- [ ] Plan backward-compatible method signatures  
- [ ] Identify all test files that exercise the component
- [ ] Create rollback plan (git checkout command ready)

### During File Change:
- [ ] Update imports (remove JWT, add auth service)
- [ ] Replace JWT operations with auth service calls
- [ ] Maintain method signatures for backward compatibility
- [ ] Add comprehensive error handling
- [ ] Update logging to indicate SSOT delegation

### After Each File Change:
- [ ] Run file-specific tests
- [ ] Run Golden Path tests  
- [ ] Check for authentication errors in logs
- [ ] Test with staging environment if critical file
- [ ] Commit changes (atomic commits for easy rollback)

### File-Specific Test Commands:
```bash
# For each modified file, run:
python tests/unit/test_[filename].py -v
python tests/integration/test_[component]_integration.py -v

# After every 3 files, run:
python tests/mission_critical/test_websocket_agent_events_suite.py

# After each critical file:
python tests/e2e/test_full_authentication_flow.py
```

---

## ERROR SCENARIOS & RECOVERY

### Common Error Patterns:

#### 1. Method Signature Mismatches
**Symptom:** TypeError: missing positional argument
**Fix:** Check backward compatibility, add default parameters
**Recovery:** Revert file, fix signature, retest

#### 2. Auth Service Connection Failures
**Symptom:** ConnectionError, timeout exceptions
**Fix:** Add circuit breaker pattern, graceful degradation
**Recovery:** Temporary fallback to cached validation

#### 3. Token Format Inconsistencies  
**Symptom:** Validation failures, 401 errors
**Fix:** Check token format conversion in auth service client
**Recovery:** Ensure consistent token format across services

#### 4. Performance Degradation
**Symptom:** Slow response times, timeout errors
**Fix:** Add token caching, optimize auth service calls
**Recovery:** Monitor latency, scale auth service if needed

---

## VALIDATION COMMANDS

### Critical Path Validation:
```bash
# Golden Path - MUST PASS after each critical file
python tests/mission_critical/test_websocket_agent_events_suite.py

# Authentication Flow - Validate login → AI response
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}'

# WebSocket Connection - Validate chat functionality  
wscat -c ws://localhost:8000/ws \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# SSOT Compliance - Validate no JWT violations
python scripts/scan_jwt_violations.py --strict
```

### Performance Validation:
```bash
# Auth latency benchmark
time curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/agents/status

# Concurrent user simulation
python tests/performance/test_concurrent_auth.py --users 100
```

This file-by-file guide ensures systematic, safe migration of all JWT operations to the auth service SSOT while maintaining Golden Path functionality and providing immediate rollback capability at each step.