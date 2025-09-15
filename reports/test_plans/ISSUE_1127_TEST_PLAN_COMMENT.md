# Issue #1127 Test Plan - SessionMiddleware Configuration Missing

## 🚨 **Test Plan Created**
Comprehensive test strategy targeting 100+ errors/hour from SessionMiddleware configuration issues in GCP deployment.

## 🎯 **Primary Focus**
**Target Error**: `netra_backend/app/middleware/gcp_auth_context_middleware.py:160` - "SessionMiddleware must be installed to access request.session"

## 📋 **Test Strategy Overview**

### **1. Integration Tests (Non-Docker) - PRIMARY**
- **SessionMiddleware Installation Validation**: Verify middleware properly installed via app_factory
- **Middleware Chain Initialization**: Test complete middleware sequence and ordering
- **Request.Session Access Patterns**: Test exact scenario from gcp_auth_context_middleware.py:160

### **2. E2E GCP Staging Tests - VALIDATION**
- **Staging Environment Validation**: Test against actual GCP deployment
- **Environment Configuration**: Verify SECRET_KEY and session backend connectivity
- **Production Parity**: Ensure staging matches production middleware configuration

### **3. Error Reproduction Tests - DEBUGGING**
- **Exact Error Reproduction**: Reproduce "SessionMiddleware must be installed" error
- **Middleware Order Issues**: Test if wrong order causes session access failures
- **GCP Environment Simulation**: Test Cloud Run environment-specific issues

## 🎯 **Critical Test Cases**

### **Test Case 1: Exact Error Location**
```python
# Target: gcp_auth_context_middleware.py:160
async def test_gcp_auth_context_middleware_session_access_exact_scenario():
    """Test exact line 160 scenario causing the error"""
    app = create_app()  # Real app factory
    # Test request.session access in auth context middleware
```

### **Test Case 2: Middleware Installation Order**
```python
def test_session_middleware_initialization_order():
    """Verify SessionMiddleware installed BEFORE auth middleware"""
    # SessionMiddleware must come before any middleware accessing sessions
```

### **Test Case 3: GCP Cloud Run Environment**
```python
def test_session_middleware_gcp_cloud_run_environment():
    """Test with GCP Cloud Run environment variables (K_SERVICE, etc.)"""
    # Simulate exact GCP deployment environment
```

## 🚀 **Execution Plan**

**Phase 1**: Integration tests (local) - Target middleware configuration issues
**Phase 2**: E2E staging tests - Validate real GCP environment
**Phase 3**: Reproduction tests - Confirm error conditions and fixes

## 📊 **Success Criteria**
- ✅ **Zero session access errors**: No "SessionMiddleware must be installed" in logs
- ✅ **Middleware order validated**: SessionMiddleware before dependent middleware
- ✅ **GCP compatibility**: All tests pass in Cloud Run simulated environment
- ✅ **Production parity**: Staging tests validate actual deployment

## 📂 **Test Files to Create**
1. `tests/integration/middleware/test_session_middleware_gcp_installation.py`
2. `tests/integration/middleware/test_middleware_chain_initialization.py`
3. `tests/e2e/gcp/test_session_middleware_staging_validation.py`
4. `tests/integration/reproduction/test_session_middleware_error_reproduction.py`

**Full Test Plan**: [ISSUE_1127_SESSIONMIDDLEWARE_TEST_PLAN.md](ISSUE_1127_SESSIONMIDDLEWARE_TEST_PLAN.md)

## 🎯 **Business Impact**
**Primary Goal**: Eliminate 100+ session-related errors per hour in GCP production
**Expected Outcome**: Zero SessionMiddleware configuration errors in deployment