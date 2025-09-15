# Issue #1127 SessionMiddleware Configuration Test Plan

## 🎯 **Test Plan Summary**
**Target Issue**: SessionMiddleware configuration missing in GCP causing 100+ errors/hour
**Error Location**: `netra_backend/app/middleware/gcp_auth_context_middleware.py:160`
**Business Impact**: P1 - High impact session failures affecting user authentication flows

## 🚨 **Critical Understanding**
The error `"SessionMiddleware must be installed to access request.session"` occurs when:
1. SessionMiddleware is not properly installed in the middleware stack
2. Middleware ordering prevents session access
3. GCP Cloud Run environment-specific configuration issues
4. Middleware initialization race conditions during startup

## 📋 **Test Categories & Strategy**

### **1. Integration Tests (Non-Docker) - PRIMARY FOCUS**
Tests that simulate GCP environment without Docker dependencies to isolate configuration issues.

#### **1.1 SessionMiddleware Installation Validation**
```python
# tests/integration/middleware/test_session_middleware_gcp_installation.py
class TestSessionMiddlewareGCPInstallation:
    """Test SessionMiddleware installation in GCP-like environments"""

    def test_session_middleware_installed_in_app_factory(self):
        """Verify SessionMiddleware is properly installed via app_factory"""

    def test_session_middleware_order_validation(self):
        """Verify SessionMiddleware is installed BEFORE auth middleware"""

    def test_session_middleware_secret_key_configuration(self):
        """Verify SECRET_KEY is properly configured from environment"""

    def test_session_middleware_gcp_environment_compatibility(self):
        """Test middleware works with GCP Cloud Run environment variables"""
```

#### **1.2 Middleware Chain Initialization Tests**
```python
# tests/integration/middleware/test_middleware_chain_initialization.py
class TestMiddlewareChainInitialization:
    """Test complete middleware chain initialization sequence"""

    def test_deterministic_middleware_startup_sequence(self):
        """Verify middleware initialization happens in correct order"""

    def test_session_middleware_available_during_request_processing(self):
        """Test session access during actual request processing"""

    def test_gcp_auth_context_middleware_session_access(self):
        """Specific test for line 160 - request.session access in GCP auth middleware"""

    def test_middleware_race_condition_prevention(self):
        """Test that middleware initialization doesn't have race conditions"""
```

#### **1.3 Request.Session Access Pattern Tests**
```python
# tests/integration/middleware/test_request_session_access_patterns.py
class TestRequestSessionAccessPatterns:
    """Test all patterns of request.session access in the codebase"""

    def test_gcp_auth_context_middleware_session_access(self):
        """Test exact scenario from gcp_auth_context_middleware.py:160"""

    def test_session_access_with_real_fastapi_request(self):
        """Test session access with real FastAPI Request object"""

    def test_session_data_persistence_across_requests(self):
        """Test session data persists correctly across requests"""

    def test_session_access_error_handling(self):
        """Test graceful handling when SessionMiddleware is missing"""
```

### **2. E2E GCP Staging Tests - VALIDATION FOCUS**
Tests that run against actual staging GCP environment to validate real deployment.

#### **2.1 GCP Staging Validation**
```python
# tests/e2e/gcp/test_session_middleware_staging_validation.py
class TestSessionMiddlewareStaginValidation:
    """E2E validation against staging GCP environment"""

    def test_staging_session_middleware_functional(self):
        """Verify SessionMiddleware works in actual staging GCP deployment"""

    def test_staging_auth_flow_with_sessions(self):
        """Test complete auth flow using sessions in staging"""

    def test_staging_websocket_session_integration(self):
        """Test WebSocket connections can access sessions in staging"""

    def test_staging_middleware_chain_health_check(self):
        """Health check specifically for middleware configuration in staging"""
```

#### **2.2 GCP Environment Configuration Tests**
```python
# tests/e2e/gcp/test_gcp_environment_session_config.py
class TestGCPEnvironmentSessionConfig:
    """Test session configuration in actual GCP environment"""

    def test_gcp_secret_key_configuration(self):
        """Verify SECRET_KEY is properly configured in GCP environment"""

    def test_gcp_session_backend_connectivity(self):
        """Test session backend (Redis) connectivity in GCP"""

    def test_gcp_cloud_run_session_persistence(self):
        """Test session persistence across Cloud Run instances"""
```

### **3. Reproduction Tests - ERROR SIMULATION**
Tests designed to reproduce the exact error condition for validation.

#### **3.1 Error Condition Reproduction**
```python
# tests/integration/reproduction/test_session_middleware_error_reproduction.py
class TestSessionMiddlewareErrorReproduction:
    """Reproduce exact error conditions from Issue #1127"""

    def test_reproduce_session_middleware_missing_error(self):
        """Reproduce 'SessionMiddleware must be installed' error"""

    def test_reproduce_gcp_auth_context_middleware_failure(self):
        """Reproduce specific failure in gcp_auth_context_middleware.py:160"""

    def test_session_access_without_middleware_installation(self):
        """Test what happens when SessionMiddleware is not installed"""

    def test_middleware_order_causing_session_access_failure(self):
        """Test if wrong middleware order causes session access issues"""
```

## 🎯 **Specific Test Scenarios**

### **Critical Test Case 1: GCP Auth Context Middleware Session Access**
**File**: `netra_backend/app/middleware/gcp_auth_context_middleware.py:160`
**Error**: `session = request.session` fails with "SessionMiddleware must be installed"

```python
async def test_gcp_auth_context_middleware_session_access_exact_scenario(self):
    """Test exact line 160 scenario from gcp_auth_context_middleware.py"""
    # Create FastAPI app with real middleware chain
    app = create_app()  # Use actual app factory

    # Create test request that simulates GCP environment
    with TestClient(app) as client:
        # Make request that triggers gcp_auth_context_middleware
        response = client.get("/health", headers={
            "X-Forwarded-For": "10.0.0.1",
            "User-Agent": "GCP-Health-Check"
        })

        # Verify no session access errors occurred
        # Check logs for "SessionMiddleware must be installed" errors
        assert response.status_code != 500
```

### **Critical Test Case 2: Middleware Initialization Order**
**Issue**: SessionMiddleware must be installed BEFORE other middleware that accesses sessions

```python
def test_session_middleware_initialization_order(self):
    """Verify SessionMiddleware is installed before auth middleware"""
    app = FastAPI()

    # Use actual middleware setup from app_factory
    from netra_backend.app.core.app_factory import setup_middleware
    setup_middleware(app)

    # Inspect middleware stack to verify order
    middleware_stack = app.middleware_stack

    # Find SessionMiddleware and auth middleware positions
    session_middleware_pos = None
    auth_middleware_pos = None

    for i, middleware in enumerate(middleware_stack):
        if "SessionMiddleware" in str(middleware):
            session_middleware_pos = i
        if "auth" in str(middleware).lower():
            auth_middleware_pos = i

    # SessionMiddleware should come BEFORE auth middleware
    assert session_middleware_pos is not None, "SessionMiddleware not found in stack"
    assert session_middleware_pos < auth_middleware_pos, "SessionMiddleware must come before auth middleware"
```

### **Critical Test Case 3: GCP Cloud Run Environment Simulation**
**Issue**: Configuration differences between local and GCP Cloud Run environments

```python
def test_session_middleware_gcp_cloud_run_environment(self):
    """Test SessionMiddleware in simulated GCP Cloud Run environment"""
    # Set GCP Cloud Run environment variables
    env = IsolatedEnvironment()
    env.set("K_SERVICE", "netra-backend")  # GCP Cloud Run marker
    env.set("K_REVISION", "1")
    env.set("PORT", "8080")
    env.set("SECRET_KEY", "gcp_test_secret_" + "x" * 32)

    # Create app with GCP environment
    app = create_app()

    with TestClient(app) as client:
        # Test session access works
        response = client.get("/health")
        assert response.status_code == 200

        # Verify no session-related errors in logs
```

## 🚀 **Test Execution Strategy**

### **Phase 1: Integration Tests (Local)**
```bash
# Run non-Docker integration tests
python tests/unified_test_runner.py --category integration --pattern "*session*middleware*" --no-docker

# Specific middleware tests
python -m pytest tests/integration/middleware/test_session_middleware_gcp_installation.py -v
python -m pytest tests/integration/middleware/test_middleware_chain_initialization.py -v
```

### **Phase 2: E2E Staging Validation**
```bash
# Run against actual staging GCP environment
python tests/unified_test_runner.py --category e2e --pattern "*session*middleware*staging*" --env staging

# Specific staging validation
python -m pytest tests/e2e/gcp/test_session_middleware_staging_validation.py --staging -v
```

### **Phase 3: Reproduction Testing**
```bash
# Reproduce exact error conditions
python -m pytest tests/integration/reproduction/test_session_middleware_error_reproduction.py -v

# Validate error conditions are fixed
python -m pytest tests/integration/reproduction/ --reproduce-errors -v
```

## 📊 **Success Criteria**

### **Test Coverage Requirements**
- ✅ **Integration Tests**: 95% coverage of SessionMiddleware initialization paths
- ✅ **E2E Tests**: 100% coverage of staging GCP environment validation
- ✅ **Reproduction Tests**: 100% reproduction of reported error conditions
- ✅ **Real Services**: All tests use real FastAPI apps, no mocks for core middleware

### **Validation Requirements**
- ✅ **No Session Access Errors**: Zero "SessionMiddleware must be installed" errors in logs
- ✅ **Middleware Order Validation**: SessionMiddleware installed before dependent middleware
- ✅ **GCP Compatibility**: All tests pass in GCP Cloud Run simulated environment
- ✅ **Production Parity**: Staging tests validate actual deployment configuration

## 🔧 **Implementation Plan**

### **Step 1: Create Integration Test Suite**
**Target**: 3 test files, ~15 test methods
**Focus**: Non-Docker integration tests for middleware configuration

### **Step 2: Implement E2E Staging Tests**
**Target**: 2 test files, ~8 test methods
**Focus**: Real staging GCP environment validation

### **Step 3: Add Reproduction Tests**
**Target**: 1 test file, ~5 test methods
**Focus**: Exact error condition reproduction

### **Step 4: Integrate with Mission Critical Suite**
**Target**: Add to mission critical test execution
**Focus**: Protect against regression in core session functionality

## 📝 **Test Files to Create**

1. `tests/integration/middleware/test_session_middleware_gcp_installation.py`
2. `tests/integration/middleware/test_middleware_chain_initialization.py`
3. `tests/integration/middleware/test_request_session_access_patterns.py`
4. `tests/e2e/gcp/test_session_middleware_staging_validation.py`
5. `tests/e2e/gcp/test_gcp_environment_session_config.py`
6. `tests/integration/reproduction/test_session_middleware_error_reproduction.py`

## 🎯 **Business Value Protection**

**Primary Goal**: Eliminate 100+ session-related errors per hour in GCP production
**Secondary Goal**: Ensure reliable user authentication and session management
**Strategic Goal**: Prevent user experience degradation from session failures

**Expected Outcome**: Zero session middleware configuration errors in production deployment