# Issue #169 SessionMiddleware Log Spam Test Plan

## 🎯 **Test Plan Summary**
**Target Issue**: SessionMiddleware log spam causing 100+ warnings per hour in production
**Error Pattern**: `"Session access failed (middleware not installed?)"` and `"SessionMiddleware must be installed"`
**Business Impact**: P1 - Log noise pollution affecting monitoring and debugging capabilities
**Root Cause**: Excessive logging in `_safe_extract_session_data()` method without rate limiting

## 🚨 **Critical Understanding**

The SessionMiddleware log spam issue occurs when:
1. **High-frequency requests** repeatedly trigger session access attempts
2. **Missing or misconfigured SessionMiddleware** causes repeated warnings
3. **No log rate limiting** allows 100+ identical warnings per hour
4. **Production environments** generate excessive log volume affecting monitoring

## 📋 **Test Categories & Strategy**

### **1. Unit Tests - LOG BEHAVIOR VALIDATION**
Tests that focus on logging patterns and rate limiting without external dependencies.

#### **1.1 Log Rate Limiting Tests**
```python
# tests/unit/middleware/test_session_middleware_log_rate_limiting.py
class TestSessionMiddlewareLogRateLimiting:
    """Test log rate limiting in SessionMiddleware error scenarios"""

    def test_session_access_failure_log_rate_limiting(self):
        """Verify session access failures don't spam logs beyond rate limit"""

    def test_repeated_session_access_generates_single_warning_per_window(self):
        """Test that 100+ session access failures generate only 1 warning per time window"""

    def test_log_rate_limiter_resets_after_time_window(self):
        """Test that log rate limiter properly resets after configured time window"""

    def test_different_error_types_have_separate_rate_limits(self):
        """Test that different session errors have independent rate limiting"""
```

#### **1.2 Session Access Pattern Validation**
```python
# tests/unit/middleware/test_gcp_auth_context_session_patterns.py
class TestGCPAuthContextSessionPatterns:
    """Test session access patterns in GCPAuthContextMiddleware"""

    def test_safe_extract_session_data_graceful_degradation(self):
        """Test _safe_extract_session_data handles all error cases gracefully"""

    def test_session_middleware_not_installed_scenario(self):
        """Test behavior when SessionMiddleware is completely absent"""

    def test_session_middleware_misconfigured_scenario(self):
        """Test behavior when SessionMiddleware is present but misconfigured"""

    def test_session_access_fallback_strategies_no_spam(self):
        """Test fallback strategies don't generate excessive log messages"""
```

### **2. Integration Tests (Non-Docker) - REQUEST SIMULATION**
Tests that simulate high-volume request scenarios to reproduce log spam.

#### **2.1 High-Volume Request Simulation**
```python
# tests/integration/middleware/test_session_middleware_log_spam_prevention.py
class TestSessionMiddlewareLogSpamPrevention:
    """Test log spam prevention under high-volume request scenarios"""

    def test_100_requests_generate_limited_session_warnings(self):
        """Test 100+ requests generate max 1 session warning per rate limit window"""

    def test_concurrent_requests_session_access_logging(self):
        """Test concurrent requests don't bypass log rate limiting"""

    def test_sustained_load_session_warning_patterns(self):
        """Test sustained load over time maintains proper log rate limiting"""

    def test_session_middleware_restoration_clears_warnings(self):
        """Test that fixing SessionMiddleware stops generating warnings"""
```

#### **2.2 Real Request Processing with Log Monitoring**
```python
# tests/integration/middleware/test_session_middleware_production_patterns.py
class TestSessionMiddlewareProductionPatterns:
    """Test production-like scenarios with comprehensive log monitoring"""

    def test_fastapi_app_with_missing_session_middleware_log_behavior(self):
        """Test FastAPI app missing SessionMiddleware generates controlled logs"""

    def test_websocket_requests_session_access_log_patterns(self):
        """Test WebSocket requests don't generate excessive session warnings"""

    def test_health_check_requests_no_session_log_spam(self):
        """Test health check endpoints don't contribute to session log spam"""

    def test_authenticated_vs_unauthenticated_request_log_differences(self):
        """Test different request types generate appropriate log levels"""
```

### **3. E2E GCP Staging Tests - PRODUCTION VALIDATION**
Tests that validate log behavior in actual staging GCP environment.

#### **3.1 GCP Staging Log Volume Validation**
```python
# tests/e2e/gcp/test_session_middleware_staging_log_validation.py
class TestSessionMiddlewareStaginLogValidation:
    """E2E validation of session middleware logging in staging GCP"""

    def test_staging_session_middleware_log_volume_within_limits(self):
        """Verify staging environment session logs stay within acceptable volume"""

    def test_staging_session_warning_frequency_compliance(self):
        """Test staging session warnings don't exceed 1 per minute threshold"""

    def test_staging_log_aggregation_session_patterns(self):
        """Test GCP log aggregation shows proper session warning patterns"""

    def test_staging_cloud_run_session_middleware_behavior(self):
        """Test Cloud Run environment session middleware logging behavior"""
```

#### **3.2 GCP Log Monitoring Integration**
```python
# tests/e2e/gcp/test_gcp_log_monitoring_session_alerts.py
class TestGCPLogMonitoringSessionAlerts:
    """Test GCP log monitoring and alerting for session issues"""

    def test_gcp_log_based_alerting_session_thresholds(self):
        """Test GCP log-based alerts trigger at appropriate session warning thresholds"""

    def test_session_middleware_health_check_log_patterns(self):
        """Test session middleware health checks generate proper log patterns"""

    def test_production_parity_session_logging_validation(self):
        """Validate staging session logging matches expected production patterns"""
```

## 🎯 **Specific Reproduction Test Scenarios**

### **Critical Test Case 1: Log Spam Reproduction**
**Issue**: 100+ identical warnings per hour for session access failures
**File**: `netra_backend/app/middleware/gcp_auth_context_middleware.py:_safe_extract_session_data`

```python
async def test_reproduce_exact_log_spam_scenario(self):
    """Reproduce exact log spam scenario from Issue #169"""

    # Create FastAPI app WITHOUT SessionMiddleware (reproduces the issue)
    app = FastAPI()
    app.add_middleware(GCPAuthContextMiddleware)  # No SessionMiddleware installed

    # Create log capture to monitor warning frequency
    with LogCapture('netra_backend.app.middleware.gcp_auth_context_middleware') as log_capture:

        # Simulate 100+ rapid requests (reproduces high volume)
        with TestClient(app) as client:
            for i in range(120):  # 120 requests to exceed 100+ threshold
                response = client.get("/health", headers={
                    "X-Request-ID": f"test-request-{i}",
                    "X-Forwarded-For": "10.0.0.1"
                })

        # CRITICAL VALIDATION: Verify log spam is controlled
        session_warnings = [record for record in log_capture.records
                           if "Session access failed" in record.getMessage()]

        # BEFORE FIX: This would be 120+ warnings
        # AFTER FIX: This should be 1-3 warnings max (with rate limiting)
        assert len(session_warnings) <= 3, f"Expected ≤3 session warnings, got {len(session_warnings)}"

        # Verify warnings contain proper context for debugging
        if session_warnings:
            assert "middleware not installed" in session_warnings[0].getMessage()
```

### **Critical Test Case 2: Rate Limiting Window Validation**
**Issue**: Rate limiting should reset after time window to allow new warnings

```python
def test_log_rate_limiting_time_window_behavior(self):
    """Test log rate limiting properly resets after time window"""

    app = FastAPI()
    middleware = GCPAuthContextMiddleware(app)
    mock_request = Mock(spec=Request)

    with LogCapture('netra_backend.app.middleware.gcp_auth_context_middleware') as log_capture:

        # First batch of session access attempts (should generate 1 warning)
        for i in range(10):
            middleware._safe_extract_session_data(mock_request)

        initial_warnings = len(log_capture.records)

        # Simulate time window passage (rate limiter should reset)
        with patch('time.time', return_value=time.time() + 300):  # 5 minutes later

            # Second batch of session access attempts (should generate new warning)
            for i in range(10):
                middleware._safe_extract_session_data(mock_request)

        final_warnings = len(log_capture.records)

        # Should have exactly 2 warnings: one for each time window
        assert final_warnings == initial_warnings + 1, f"Expected 2 total warnings, got {final_warnings}"
```

### **Critical Test Case 3: Production Load Simulation**
**Issue**: Sustained production load should maintain log rate limiting

```python
async def test_production_load_session_logging_behavior(self):
    """Test session logging under sustained production-like load"""

    app = create_app()  # Use actual app factory

    # Remove SessionMiddleware to simulate misconfiguration
    app.middleware_stack = [m for m in app.middleware_stack
                           if "SessionMiddleware" not in str(type(m))]

    with LogCapture('netra_backend.app.middleware.gcp_auth_context_middleware') as log_capture:

        # Simulate sustained load over 10 minutes
        with TestClient(app) as client:
            start_time = time.time()
            request_count = 0

            while time.time() - start_time < 600:  # 10 minutes
                client.get("/health")
                request_count += 1
                await asyncio.sleep(0.1)  # 10 requests per second

        session_warnings = [r for r in log_capture.records if "Session access failed" in r.getMessage()]

        # Under sustained load, should generate max 1 warning per 5-minute window = 2 warnings max
        assert len(session_warnings) <= 2, f"Sustained load generated {len(session_warnings)} warnings (expected ≤2)"
        assert request_count > 1000, f"Expected >1000 requests for load test, got {request_count}"
```

## 🚀 **Test Execution Strategy**

### **Phase 1: Unit Test Validation (Local)**
```bash
# Test log rate limiting behavior
python tests/unified_test_runner.py --category unit --pattern "*session*middleware*log*" --no-docker

# Test session access patterns
python -m pytest tests/unit/middleware/test_session_middleware_log_rate_limiting.py -v
python -m pytest tests/unit/middleware/test_gcp_auth_context_session_patterns.py -v
```

### **Phase 2: Integration Reproduction Testing (Local)**
```bash
# Reproduce log spam scenarios
python tests/unified_test_runner.py --category integration --pattern "*session*spam*" --no-docker

# Test high-volume scenarios
python -m pytest tests/integration/middleware/test_session_middleware_log_spam_prevention.py -v
python -m pytest tests/integration/middleware/test_session_middleware_production_patterns.py -v
```

### **Phase 3: E2E Staging Validation (GCP)**
```bash
# Validate staging log behavior
python tests/unified_test_runner.py --category e2e --pattern "*session*log*staging*" --env staging

# Monitor actual GCP log volumes
python -m pytest tests/e2e/gcp/test_session_middleware_staging_log_validation.py --staging -v
```

## 📊 **Success Criteria**

### **Log Rate Limiting Requirements**
- ✅ **Session Access Warnings**: Max 1 warning per 5-minute window per error type
- ✅ **High-Volume Resilience**: 1000+ requests generate ≤2 session warnings total
- ✅ **Rate Limiter Reset**: Time window properly resets rate limiting counters
- ✅ **Error Type Isolation**: Different session errors have independent rate limits

### **Production Validation Requirements**
- ✅ **Staging Log Volume**: Session warnings stay below 12/hour threshold
- ✅ **GCP Log Aggregation**: Proper log patterns visible in Cloud Logging
- ✅ **Alert Threshold Compliance**: Warnings stay below alerting thresholds
- ✅ **Production Parity**: Staging behavior matches expected production patterns

### **Business Impact Validation**
- ✅ **Monitoring Clarity**: Session issues are visible but don't overwhelm logs
- ✅ **Debugging Capability**: Sufficient information for troubleshooting retained
- ✅ **Alert Fatigue Prevention**: Log volume doesn't trigger false positive alerts
- ✅ **Cost Optimization**: Reduced log volume decreases GCP logging costs

## 🔧 **Implementation Plan**

### **Step 1: Create Log Rate Limiting Tests**
**Target**: 2 unit test files, ~8 test methods
**Focus**: Log rate limiting behavior and session access patterns

### **Step 2: Implement High-Volume Simulation Tests**
**Target**: 2 integration test files, ~8 test methods
**Focus**: Reproduce log spam scenarios and validate prevention

### **Step 3: Add E2E Production Validation**
**Target**: 2 E2E test files, ~6 test methods
**Focus**: Validate staging/production log behavior compliance

### **Step 4: Integrate with Mission Critical Suite**
**Target**: Add to mission critical test execution
**Focus**: Prevent regression in log spam prevention

## 📝 **Test Files to Create**

1. `tests/unit/middleware/test_session_middleware_log_rate_limiting.py`
2. `tests/unit/middleware/test_gcp_auth_context_session_patterns.py`
3. `tests/integration/middleware/test_session_middleware_log_spam_prevention.py`
4. `tests/integration/middleware/test_session_middleware_production_patterns.py`
5. `tests/e2e/gcp/test_session_middleware_staging_log_validation.py`
6. `tests/e2e/gcp/test_gcp_log_monitoring_session_alerts.py`

## 🎯 **Key Validation Points**

### **Before Fix (Expected Failing Behavior)**
```python
# This test should FAIL before the fix is applied
def test_log_spam_reproduction_before_fix(self):
    """Test that reproduces the original log spam issue (should fail initially)"""
    # 100+ requests without SessionMiddleware
    # Expected: 100+ warning messages (FAILING behavior)
    # After fix: 1-3 warning messages (PASSING behavior)
```

### **After Fix (Expected Passing Behavior)**
```python
def test_log_rate_limiting_after_fix(self):
    """Test that validates log rate limiting works correctly (should pass after fix)"""
    # 100+ requests without SessionMiddleware
    # Expected: 1-3 warning messages max (PASSING behavior)
    # Validates rate limiting is working properly
```

## 📈 **Business Value Protection**

**Primary Goal**: Eliminate log noise pollution affecting monitoring and debugging
**Secondary Goal**: Maintain visibility into actual SessionMiddleware configuration issues
**Strategic Goal**: Optimize GCP logging costs and alert accuracy

**Expected Outcome**: 95% reduction in session-related log volume while maintaining diagnostic capability

---

*This test plan ensures comprehensive validation of SessionMiddleware log spam prevention while maintaining production monitoring effectiveness.*