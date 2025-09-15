# 🧪 Issue #926 Test Plan: Auth Service Session Management Initialization Failure

**Issue:** Auth Service Session Management Initialization Failure - 'auth_service' Undefined
**Session:** agent-session-2025-09-13-2100
**Priority:** P1 Critical - Affects service health endpoints and shutdown procedures

## 🔍 Issue Analysis

### Root Cause
Variable scope mismatch between import location and usage locations in `auth_service/main.py`:

- **Line 249:** Correct local import in lifespan function scope
- **Line 348:** Undefined `auth_service` in shutdown function scope
- **Lines 665-667:** Undefined `auth_service` in health endpoint scope

### Technical Details
The issue occurs because:
1. `auth_service` is imported locally within the lifespan function (line 249-252)
2. Other functions (shutdown and health endpoints) attempt to use `auth_service` without importing it
3. This causes `NameError: name 'auth_service' is not defined` at runtime

## 🎯 Test Strategy

### Testing Approach
Following CLAUDE.md directives:
- **Real Services First:** Use actual auth service, not mocks
- **SSOT Testing Patterns:** Use unified test infrastructure
- **Non-Docker Focus:** Unit, integration, and staging GCP e2e tests only
- **Business Value Protection:** Ensure $500K+ ARR Golden Path functionality

### Test Progression
**Unit → Integration → E2E** progression to isolate and validate fixes:

## 📋 Test Plan Details

### 1. Unit Tests

#### Test File: `auth_service/tests/unit/test_auth_service_variable_scope.py`

**Purpose:** Test individual functions with undefined auth_service references

#### Test Cases:

1. **test_lifespan_function_auth_service_import**
   ```python
   async def test_lifespan_function_auth_service_import():
       """Test that lifespan function properly imports auth_service"""
       # Setup: Mock app context
       # Execute: Call lifespan function
       # Assert: auth_service is properly imported and accessible
   ```

2. **test_shutdown_function_auth_service_access**
   ```python
   async def test_shutdown_function_auth_service_access():
       """Test shutdown function can access auth_service without NameError"""
       # Setup: Simulate shutdown scenario
       # Execute: Call close_redis function from shutdown
       # Assert: No NameError occurs, auth_service is accessible
   ```

3. **test_health_endpoint_auth_service_access**
   ```python
   async def test_health_endpoint_auth_service_access():
       """Test health endpoint can access auth_service for session management check"""
       # Setup: Mock health endpoint context
       # Execute: Call health endpoint with session management check
       # Assert: No NameError occurs, session management status is retrievable
   ```

4. **test_variable_scope_isolation**
   ```python
   def test_variable_scope_isolation():
       """Test that variable scope isolation causes the issue"""
       # Setup: Mock function scopes
       # Execute: Attempt to access variables across scope boundaries
       # Assert: Proper error handling when scope mismatch occurs
   ```

**Expected Failures:**
- Tests 2 and 3 should FAIL before fix is applied
- Tests should demonstrate the exact NameError scenario

### 2. Integration Tests

#### Test File: `auth_service/tests/integration/test_auth_service_initialization_sequence.py`

**Purpose:** Test auth service initialization sequence with real service components

#### Test Cases:

1. **test_auth_service_startup_initialization_sequence**
   ```python
   async def test_auth_service_startup_initialization_sequence():
       """Test complete auth service startup sequence with proper variable scope"""
       # Setup: Real FastAPI app with lifespan
       # Execute: Full startup sequence including lifespan function
       # Assert: auth_service is properly initialized and accessible
   ```

2. **test_auth_service_shutdown_sequence**
   ```python
   async def test_auth_service_shutdown_sequence():
       """Test auth service shutdown sequence accessing auth_service"""
       # Setup: Running auth service with initialized auth_service
       # Execute: Trigger shutdown sequence
       # Assert: Shutdown completes without NameError, Redis connections close
   ```

3. **test_health_endpoint_session_management_check**
   ```python
   async def test_health_endpoint_session_management_check():
       """Test health endpoint session management capability check"""
       # Setup: Running auth service with real AuthService instance
       # Execute: Call /health/auth endpoint
       # Assert: Session management status is properly determined
   ```

4. **test_redis_connection_lifecycle**
   ```python
   async def test_redis_connection_lifecycle():
       """Test Redis connection lifecycle through auth service"""
       # Setup: Auth service with Redis enabled
       # Execute: Startup → Check Redis status → Shutdown
       # Assert: Redis lifecycle managed properly without variable scope errors
   ```

**Expected Failures:**
- Shutdown and health endpoint tests should FAIL before fix
- Should demonstrate real runtime failures in integration context

### 3. E2E Tests (Staging GCP)

#### Test File: `tests/e2e/staging/test_auth_service_variable_scope_e2e.py`

**Purpose:** Test auth service on staging GCP with real deployment conditions

#### Test Cases:

1. **test_auth_service_health_endpoints_staging**
   ```python
   async def test_auth_service_health_endpoints_staging():
       """Test all auth service health endpoints on staging"""
       # Setup: Staging auth service URL
       # Execute: Call /health, /health/auth, /health/ready endpoints
       # Assert: All endpoints return proper responses without errors
   ```

2. **test_auth_service_session_management_capability**
   ```python
   async def test_auth_service_session_management_capability():
       """Test session management capability reporting on staging"""
       # Setup: Staging auth service with Redis
       # Execute: Call /health/auth endpoint to check capabilities
       # Assert: Session management capability is properly reported
   ```

3. **test_auth_service_graceful_shutdown_staging**
   ```python
   async def test_auth_service_graceful_shutdown_staging():
       """Test graceful shutdown behavior on staging (through restart)"""
       # Setup: Monitor staging auth service logs
       # Execute: Trigger service restart through Cloud Run
       # Assert: No NameError in shutdown logs, graceful Redis closure
   ```

4. **test_golden_path_auth_flow_with_session_management**
   ```python
   async def test_golden_path_auth_flow_with_session_management():
       """Test complete Golden Path auth flow including session management"""
       # Setup: Staging environment
       # Execute: Login → Token validation → Session check → Logout
       # Assert: Complete flow works without variable scope errors
   ```

**Success Criteria:**
- All endpoints respond without NameError
- Health endpoints properly report session management status
- Golden Path auth functionality unaffected

## 🔧 Test Implementation Details

### Test Infrastructure Requirements

1. **SSOT Test Base Classes**
   ```python
   from test_framework.ssot.base_test_case import SSotAsyncTestCase
   from test_framework.ssot.mock_factory import SSotMockFactory
   ```

2. **Real Service Configuration**
   ```python
   # Use real auth service, not mocks
   from auth_service.auth_core.services.auth_service import AuthService
   ```

3. **Environment Setup**
   ```python
   from shared.isolated_environment import get_env
   # Use staging environment for E2E tests
   ```

### Mock Strategy (Unit Tests Only)

**Principle:** Real services preferred, mocks only for unit test isolation

```python
# GOOD: Mock only external dependencies for unit tests
mock_redis_client = SSotMockFactory.create_mock_redis_client()

# BAD: Don't mock the auth service itself in integration tests
# mock_auth_service = Mock()  # This defeats the purpose
```

### Test Data and Fixtures

1. **User Context Isolation**
   ```python
   @pytest.fixture
   async def isolated_auth_context():
       """Create isolated auth service context for testing"""
       # Factory pattern for multi-user isolation
   ```

2. **Redis Test Configuration**
   ```python
   @pytest.fixture
   def test_redis_config():
       """Redis configuration for testing"""
       # Real Redis instance for integration tests
   ```

### Expected Failure Modes

#### Before Fix Applied:
1. **Unit Tests:** `NameError: name 'auth_service' is not defined` in shutdown and health functions
2. **Integration Tests:** Service startup succeeds but shutdown/health checks fail
3. **E2E Tests:** Health endpoints return 500 errors due to undefined variable

#### After Fix Applied:
1. **Unit Tests:** All variable scope tests pass
2. **Integration Tests:** Complete initialization and shutdown sequence works
3. **E2E Tests:** All health endpoints return proper status

## 📊 Success Criteria

### Fix Validation Checklist

- [ ] **Unit Tests Pass:** All variable scope unit tests pass
- [ ] **Integration Tests Pass:** Complete auth service lifecycle works
- [ ] **E2E Tests Pass:** Staging health endpoints work without errors
- [ ] **No Regressions:** Golden Path auth functionality unaffected
- [ ] **Error Handling:** Proper error handling vs silent failures
- [ ] **Health Endpoint Accuracy:** Session management status accurately reported

### Business Impact Validation

- [ ] **$500K+ ARR Protection:** Golden Path auth flow works end-to-end
- [ ] **Service Monitoring:** Health endpoints provide accurate service status
- [ ] **Operational Reliability:** Graceful shutdown works without errors
- [ ] **Session Management:** Redis session capabilities properly detected

### Performance Requirements

- [ ] **Startup Time:** Auth service startup time not degraded
- [ ] **Health Endpoint Response:** Health endpoints respond < 1 second
- [ ] **Shutdown Time:** Graceful shutdown completes within timeout
- [ ] **Memory Usage:** No memory leaks from variable scope fixes

## 🚀 Test Execution Plan

### Phase 1: Unit Test Development
1. Create failing unit tests that reproduce the NameError
2. Validate tests fail consistently before fix
3. Prepare test infrastructure and mocks

### Phase 2: Integration Test Implementation
1. Build integration tests with real auth service components
2. Test complete initialization and shutdown sequences
3. Validate Redis lifecycle management

### Phase 3: E2E Staging Validation
1. Deploy tests to staging environment
2. Validate health endpoints with real Cloud Run deployment
3. Test Golden Path auth flow end-to-end

### Phase 4: Fix Application and Validation
1. Apply variable scope fixes to auth_service/main.py
2. Re-run all test phases to validate fixes
3. Ensure no regressions in existing functionality

## 📝 Test Deliverables

1. **Unit Test Suite:** `auth_service/tests/unit/test_auth_service_variable_scope.py`
2. **Integration Test Suite:** `auth_service/tests/integration/test_auth_service_initialization_sequence.py`
3. **E2E Test Suite:** `tests/e2e/staging/test_auth_service_variable_scope_e2e.py`
4. **Test Execution Report:** Results from all test phases
5. **Business Impact Assessment:** Validation of Golden Path functionality

## 🔗 Related Documentation

- **Issue #926:** Auth Service Session Management Initialization Failure
- **CLAUDE.md:** Testing directives and business value priorities
- **TEST_CREATION_GUIDE.md:** Comprehensive testing methodology
- **USER_CONTEXT_ARCHITECTURE.md:** Factory patterns for multi-user isolation
- **GOLDEN_PATH_USER_FLOW_COMPLETE.md:** Business-critical user authentication flow

---

**Next Steps:** Implement failing unit tests first, then progress through integration and E2E phases to validate the complete fix.