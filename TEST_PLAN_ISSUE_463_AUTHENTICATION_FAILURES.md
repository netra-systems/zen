# 🧪 Issue #463 Authentication Failures - Comprehensive Test Plan

**Issue**: [#463](https://github.com/your-org/netra-core-generation-1/issues/463) - WebSocket authentication failures in staging
**Priority**: P0 - Blocks chat functionality (90% of platform value)
**Environment**: GCP Staging
**Root Cause**: Missing environment variables (`SERVICE_SECRET`, `JWT_SECRET`, `AUTH_SERVICE_URL`)

## 📋 Business Impact Assessment

**Critical Systems Affected:**
- WebSocket authentication handshake
- Service user `service:netra-backend` authentication
- Chat functionality (90% of platform value)
- Frontend-backend communication
- Internal service-to-service authentication

**Error Pattern:**
```javascript
WebSocket connection to 'wss://api.staging.netrasystems.ai/ws' failed
Authentication failure: Authentication error (code 1006)
```

**Root Cause Chain:**
1. Service user `service:netra-backend` attempts WebSocket authentication
2. `get_request_scoped_db_session()` creates session with service context
3. Authentication middleware rejects 403 due to missing `SERVICE_SECRET`
4. WebSocket handshake fails with code 1006
5. Frontend unable to establish real-time communication

## 🎯 Test Categories and Strategy

Following `reports/testing/TEST_CREATION_GUIDE.md` and avoiding Docker requirements:

### Category 1: Unit Tests
**Focus**: Service user authentication logic isolation
**Infrastructure**: None required
**Mocks**: External auth service only

### Category 2: Integration Tests (Non-Docker)
**Focus**: Authentication middleware and service interactions
**Infrastructure**: Local services (no Docker)
**Mocks**: External APIs only

### Category 3: E2E GCP Staging Tests
**Focus**: Complete WebSocket authentication flow
**Infrastructure**: Full staging environment
**Mocks**: NONE - Everything must be real

## 📝 Detailed Test Plan

### Phase 1: Unit Tests - Service Authentication Logic

#### Test 1.1: Service User Context Generation
**Location**: `tests/unit/auth/test_service_user_authentication.py`
**Purpose**: Validate service user context creation and format

```python
class TestServiceUserAuthentication(SSotBaseTestCase):
    """Unit tests for service user authentication logic."""
    
    def test_get_service_user_context_format(self):
        """Test service user context returns proper format."""
        # Expected: "service:netra-backend" format
        # Test missing SERVICE_ID handling
        # Test environment variable precedence
        
    def test_service_user_context_with_missing_service_id(self):
        """Test behavior when SERVICE_ID not configured."""
        # Should fail gracefully with clear error
        
    def test_service_user_context_environment_precedence(self):
        """Test SERVICE_ID from config vs environment."""
        # Configuration system vs environment variables
```

#### Test 1.2: AuthServiceClient Service Validation
**Location**: `tests/unit/auth/test_auth_service_client_service_validation.py`
**Purpose**: Test `validate_service_user_context()` method

```python
class TestAuthServiceClientServiceValidation(SSotBaseTestCase):
    """Test AuthServiceClient service user validation."""
    
    def test_validate_service_user_context_success(self):
        """Test successful service user validation."""
        # Valid SERVICE_SECRET and SERVICE_ID
        # Should return {"valid": True}
        
    def test_validate_service_user_context_missing_service_secret(self):
        """Test validation with missing SERVICE_SECRET."""
        # Should return {"valid": False, "error": "missing_service_credentials"}
        
    def test_validate_service_user_context_service_id_mismatch(self):
        """Test validation with mismatched service IDs."""
        # Should log warning but allow validation
        
    def test_validate_service_user_context_invalid_service_id(self):
        """Test validation with invalid service ID format."""
        # Should return {"valid": False, "error": "invalid_service_id"}
```

#### Test 1.3: Request Scoped DB Session Service Authentication
**Location**: `tests/unit/dependencies/test_request_scoped_db_session_service_auth.py`
**Purpose**: Test service authentication in session creation

```python
class TestRequestScopedDbSessionServiceAuth(SSotBaseTestCase):
    """Test service authentication in database session creation."""
    
    @patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_service_user_context')
    async def test_get_request_scoped_db_session_service_user_success(self, mock_validate):
        """Test successful service user session creation."""
        mock_validate.return_value = {"valid": True, "service_id": "netra-backend"}
        # Test session creation succeeds with service user
        
    @patch('netra_backend.app.clients.auth_client_core.AuthServiceClient.validate_service_user_context')
    async def test_get_request_scoped_db_session_service_auth_failure(self, mock_validate):
        """Test service user session creation with auth failure."""
        mock_validate.return_value = {"valid": False, "error": "missing_service_credentials"}
        # Test session creation logs error but continues (for internal operations)
        
    async def test_get_request_scoped_db_session_comprehensive_logging(self):
        """Test comprehensive logging during service user session creation."""
        # Verify all authentication context is logged
        # Test error context in case of failures
```

### Phase 2: Integration Tests (Non-Docker) - Authentication Middleware

#### Test 2.1: Environment Variable Validation
**Location**: `tests/integration/auth/test_environment_variable_validation.py`
**Purpose**: Test authentication with various environment configurations

```python
class TestEnvironmentVariableValidation(BaseIntegrationTest):
    """Integration tests for environment variable authentication."""
    
    def setUp(self):
        """Setup isolated environment for each test."""
        self.env = IsolatedEnvironment()
        
    @pytest.mark.integration
    async def test_authentication_with_all_required_variables(self):
        """Test authentication when all variables are present."""
        self.env.set("SERVICE_SECRET", "test-service-secret-32-chars", "test")
        self.env.set("JWT_SECRET_KEY", "test-jwt-secret-32-chars", "test")
        self.env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        # Test successful authentication
        
    @pytest.mark.integration
    async def test_authentication_missing_service_secret(self):
        """Test authentication failure with missing SERVICE_SECRET."""
        # Remove SERVICE_SECRET from environment
        # Expect 403 authentication errors
        
    @pytest.mark.integration
    async def test_authentication_missing_jwt_secret(self):
        """Test authentication failure with missing JWT_SECRET."""
        # Remove JWT_SECRET_KEY from environment
        # Expect JWT validation errors
        
    @pytest.mark.integration
    async def test_authentication_missing_auth_service_url(self):
        """Test authentication failure with missing AUTH_SERVICE_URL."""
        # Remove AUTH_SERVICE_URL from environment
        # Expect service discovery errors
```

#### Test 2.2: Authentication Middleware Behavior
**Location**: `tests/integration/auth/test_authentication_middleware_behavior.py`
**Purpose**: Test middleware's handling of service users

```python
class TestAuthenticationMiddlewareBehavior(BaseIntegrationTest):
    """Integration tests for authentication middleware behavior."""
    
    @pytest.mark.integration
    async def test_middleware_service_user_authentication(self, real_services_fixture):
        """Test middleware authentication of service users."""
        # Create service user request
        # Verify middleware validates using service credentials
        
    @pytest.mark.integration
    async def test_middleware_service_user_403_reproduction(self, real_services_fixture):
        """Reproduce the 403 error with service users."""
        # Intentionally misconfigure service authentication
        # Reproduce exact error from issue #463
        
    @pytest.mark.integration
    async def test_middleware_service_user_vs_regular_user_auth(self, real_services_fixture):
        """Test middleware handles service vs regular users differently."""
        # Compare authentication flows
        # Verify different validation paths
```

#### Test 2.3: Service-to-Service Authentication Scenarios
**Location**: `tests/integration/auth/test_service_to_service_authentication.py`
**Purpose**: Test complete service-to-service authentication flow

```python
class TestServiceToServiceAuthentication(BaseIntegrationTest):
    """Test service-to-service authentication scenarios."""
    
    @pytest.mark.integration
    async def test_backend_to_auth_service_authentication(self, real_services_fixture):
        """Test netra-backend authenticating to auth service."""
        # Simulate internal service call
        # Verify service credentials are used
        
    @pytest.mark.integration
    async def test_service_authentication_token_generation(self, real_services_fixture):
        """Test service token generation and validation."""
        # Test service token creation
        # Verify service token validation
        
    @pytest.mark.integration
    async def test_service_authentication_failure_recovery(self, real_services_fixture):
        """Test recovery from service authentication failures."""
        # Test retry logic
        # Test graceful degradation
```

### Phase 3: E2E GCP Staging Tests - Complete WebSocket Flow

#### Test 3.1: WebSocket Authentication Flow Staging
**Location**: `tests/e2e/staging/test_websocket_authentication_flow_staging.py`
**Purpose**: Test complete WebSocket authentication in staging

```python
class TestWebSocketAuthenticationFlowStaging(BaseE2ETest):
    """E2E staging tests for WebSocket authentication flow."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_websocket_connection_establishment_staging(self):
        """Test WebSocket connection establishment in staging."""
        # Connect to wss://api.staging.netrasystems.ai/ws
        # Verify successful handshake
        # Test authentication headers and tokens
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_websocket_authentication_error_reproduction_staging(self):
        """Reproduce the exact authentication error from issue #463."""
        # Intentionally trigger the authentication failure
        # Verify error code 1006
        # Capture complete error context
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_websocket_service_user_authentication_staging(self):
        """Test service user authentication in WebSocket context."""
        # Test service:netra-backend user authentication
        # Verify service credentials are used
        # Test complete chat functionality
```

#### Test 3.2: Frontend WebSocket Integration Staging
**Location**: `tests/e2e/staging/test_frontend_websocket_integration_staging.py`
**Purpose**: Test frontend WebSocket integration in staging

```python
class TestFrontendWebSocketIntegrationStaging(BaseE2ETest):
    """E2E staging tests for frontend WebSocket integration."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_frontend_websocket_connection_staging(self):
        """Test frontend WebSocket connection in staging environment."""
        # Use real frontend client
        # Test complete authentication flow
        # Verify WebSocket events are received
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_frontend_websocket_authentication_recovery_staging(self):
        """Test frontend recovery from WebSocket authentication failures."""
        # Test retry logic in frontend
        # Test user experience during failures
        # Test graceful error handling
```

#### Test 3.3: Chat Functionality End-to-End Staging
**Location**: `tests/e2e/staging/test_chat_functionality_e2e_staging.py`
**Purpose**: Test complete chat functionality (90% of platform value)

```python
class TestChatFunctionalityE2EStaging(BaseE2ETest):
    """E2E staging tests for complete chat functionality."""
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.mission_critical
    async def test_complete_chat_flow_staging(self):
        """Test complete chat flow in staging environment."""
        # User login → WebSocket connection → Agent message → Response
        # Verify all 5 WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
        # Test business value delivery
        
    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_chat_authentication_failure_impact_staging(self):
        """Test impact of authentication failures on chat functionality."""
        # Test user experience when authentication fails
        # Verify error messaging and recovery paths
```

### Phase 4: Performance and Reliability Tests

#### Test 4.1: Authentication Performance Under Load
**Location**: `tests/performance/test_authentication_performance.py`
**Purpose**: Test authentication performance with concurrent users

```python
class TestAuthenticationPerformance(BaseIntegrationTest):
    """Performance tests for authentication system."""
    
    @pytest.mark.performance
    async def test_concurrent_service_user_authentication(self):
        """Test service user authentication under concurrent load."""
        # Test multiple service authentication requests
        # Verify no race conditions in service validation
        
    @pytest.mark.performance
    async def test_websocket_authentication_performance(self):
        """Test WebSocket authentication performance."""
        # Test multiple WebSocket connections
        # Verify authentication doesn't become bottleneck
```

#### Test 4.2: Authentication Error Recovery
**Location**: `tests/reliability/test_authentication_error_recovery.py`
**Purpose**: Test system recovery from authentication failures

```python
class TestAuthenticationErrorRecovery(BaseIntegrationTest):
    """Reliability tests for authentication error recovery."""
    
    @pytest.mark.reliability
    async def test_authentication_service_recovery(self):
        """Test recovery when auth service becomes unavailable."""
        # Test graceful degradation
        # Test service restoration recovery
        
    @pytest.mark.reliability
    async def test_environment_variable_recovery(self):
        """Test recovery from environment variable misconfigurations."""
        # Test dynamic reconfiguration
        # Test system restart recovery
```

## 🚨 Test Execution Priority

### Priority 1: Critical Business Impact (Run First)
1. **Phase 3.3**: Chat Functionality E2E Staging - Validates 90% of platform value
2. **Phase 3.1**: WebSocket Authentication Flow Staging - Core issue reproduction
3. **Phase 2.2**: Authentication Middleware Behavior - Root cause validation

### Priority 2: Root Cause Analysis (Run Second)
4. **Phase 1.3**: Request Scoped DB Session Service Auth - Pinpoint failure location
5. **Phase 2.1**: Environment Variable Validation - Configuration validation
6. **Phase 2.3**: Service-to-Service Authentication - Internal communication

### Priority 3: Comprehensive Coverage (Run Third)
7. **Phase 1.1, 1.2**: Unit Tests - Logic validation
8. **Phase 3.2**: Frontend WebSocket Integration - User experience
9. **Phase 4.1, 4.2**: Performance and Reliability - System robustness

## 🔧 Test Environment Setup

### Unit Tests
```bash
# No infrastructure required
python -m pytest tests/unit/auth/ -v --no-cov
```

### Integration Tests (Non-Docker)
```bash
# Start local services (non-Docker)
python tests/unified_test_runner.py --category integration --no-docker
```

### E2E Staging Tests
```bash
# Use real staging environment
python tests/unified_test_runner.py --category e2e --env staging --real-services
```

## 📊 Success Criteria

### Tests Must FAIL Initially (Reproducing Issue)
- ✅ WebSocket connection tests fail with code 1006
- ✅ Service user authentication tests fail with 403 errors
- ✅ Chat functionality tests fail due to WebSocket failures
- ✅ Environment variable tests identify missing configurations

### Tests Must PASS After Remediation
- ✅ All WebSocket connections establish successfully
- ✅ Service user authentication validates correctly
- ✅ Complete chat flow works end-to-end
- ✅ All 5 WebSocket events are sent properly
- ✅ Performance tests show no degradation

## 🎯 Expected Test Outcomes

### Before Fix (Tests Should Fail)
```
FAILED test_websocket_connection_establishment_staging - WebSocket connection failed (1006)
FAILED test_service_user_authentication_403_reproduction - Expected 403 error reproduced
FAILED test_chat_functionality_e2e_staging - Chat functionality blocked by auth failure
FAILED test_environment_variable_validation_missing_service_secret - SERVICE_SECRET not found
```

### After Fix (Tests Should Pass)
```
PASSED test_websocket_connection_establishment_staging - WebSocket connected successfully
PASSED test_service_user_authentication_success - Service authentication validated
PASSED test_chat_functionality_e2e_staging - Complete chat flow working
PASSED test_environment_variable_validation_all_present - All required variables configured
```

## 🔍 Debugging and Diagnostics

### Authentication Debug Commands
```bash
# Test service authentication locally
python -c "
from netra_backend.app.clients.auth_client_core import AuthServiceClient
import asyncio
async def test():
    client = AuthServiceClient()
    result = await client.validate_service_user_context('netra-backend', 'test')
    print(f'Validation result: {result}')
asyncio.run(test())
"

# Test environment variable configuration
python -c "
from shared.isolated_environment import get_env
env = get_env()
print(f'SERVICE_SECRET: {bool(env.get(\"SERVICE_SECRET\"))}')
print(f'JWT_SECRET_KEY: {bool(env.get(\"JWT_SECRET_KEY\"))}')
print(f'AUTH_SERVICE_URL: {env.get(\"AUTH_SERVICE_URL\")}')
"

# Test WebSocket connection directly
python -c "
import asyncio
import websockets
async def test():
    try:
        async with websockets.connect('wss://api.staging.netrasystems.ai/ws') as ws:
            print('WebSocket connection successful')
    except Exception as e:
        print(f'WebSocket connection failed: {e}')
asyncio.run(test())
"
```

## 📋 Implementation Checklist

### Test Creation Phase
- [ ] Create all unit test files following naming conventions
- [ ] Create all integration test files with real service fixtures
- [ ] Create all E2E staging test files with proper markers
- [ ] Add business value justification (BVJ) comments to all tests
- [ ] Follow SSOT patterns from test_framework/

### Test Validation Phase
- [ ] Run unit tests and verify they fail initially (reproducing issue)
- [ ] Run integration tests with isolated environment setup
- [ ] Run E2E staging tests with real staging environment
- [ ] Verify all tests use real services (no mocks in integration/E2E)
- [ ] Verify comprehensive error logging and diagnostics

### Post-Remediation Phase
- [ ] Re-run all tests after issue remediation is complete
- [ ] Verify all tests pass after authentication fixes
- [ ] Validate WebSocket functionality works end-to-end
- [ ] Confirm chat functionality (90% of platform value) is restored
- [ ] Update test documentation with lessons learned

---

**Test Plan Status**: ✅ COMPREHENSIVE PLAN CREATED  
**Next Step**: Execute test creation following the detailed specifications above  
**Business Impact**: Protects $500K+ ARR by validating authentication fixes for core chat functionality

This test plan ensures comprehensive coverage of the authentication failure in issue #463, following all testing best practices and focusing on business value delivery while avoiding Docker requirements as specified.