# GitHub Issue #411 - Docker Timeout Remediation Plan

**Generated:** 2025-09-11  
**Issue:** Docker timeout enforcement failure causing WebSocket test hangs  
**Business Impact:** Cannot validate $500K+ ARR chat functionality  
**Priority:** P0 CRITICAL - Blocking mission critical test execution

## CONFIRMED PROBLEM ANALYSIS

### Root Cause Analysis
**Primary Issue:** `UnifiedDockerManager.wait_for_services(timeout=10)` takes 13.48s (35% overrun)
- **Expected behavior:** Timeout after exactly 10 seconds
- **Actual behavior:** Continues checking for 13.48 seconds
- **Impact:** WebSocket tests hang for 60+ seconds waiting for Docker services

### Test Results Evidence
```bash
# Confirmed test execution results:
test_framework/tests/test_unified_docker_manager_timeout.py::test_wait_for_services_timeout_enforcement
FAILED - Expected timeout=10s, actual=13.48s (35% overrun)

# Mission critical WebSocket tests:
tests/mission_critical/test_websocket_agent_events_suite.py
TIMEOUT - Hangs for 120+ seconds waiting for Docker services
```

### Business Impact
- **$500K+ ARR Risk:** Cannot validate core chat functionality
- **Developer Productivity:** WebSocket test feedback delayed from <10s to 120s+ 
- **CI/CD Pipeline:** Mission critical tests blocked, preventing deployments
- **Customer Experience:** Chat reliability cannot be validated

## TECHNICAL ANALYSIS

### Current Implementation Issues

#### 1. Docker Subprocess Timeout Missing
**File:** `/test_framework/unified_docker_manager.py`  
**Method:** `_is_service_healthy()` → `_run_subprocess_safe()`  
**Issue:** Docker inspect commands lack explicit timeout parameters

```python
# CURRENT (PROBLEMATIC):
def _is_service_healthy(self, env_name: str, service_name: str) -> bool:
    cmd = ["docker", "inspect", "--format='{{.State.Health.Status}}'", container_name]
    result = _run_subprocess_safe(cmd)  # ❌ NO TIMEOUT - Can hang indefinitely
```

#### 2. Inefficient Health Check Loop
**Issue:** 2-second sleep intervals create cumulative timeout drift
```python
# CURRENT (PROBLEMATIC):
while time.time() - start_time < timeout:
    # ... health checks ...
    time.sleep(2)  # ❌ ADDS 2s to timeout calculation
```

#### 3. Missing Docker Availability Pre-Check
**Issue:** Tests attempt Docker operations without verifying Docker daemon availability
```python
# MISSING: Fast Docker availability check before attempting service orchestration
```

### WebSocket Test Infrastructure Issues

#### 1. Hard-Coded Docker Dependencies
**File:** `/tests/mission_critical/test_websocket_agent_events_suite.py`  
**Issue:** Tests fail hard when Docker unavailable, no graceful degradation

```python
# CURRENT (PROBLEMATIC):
# @require_docker_services()  # Temporarily disabled - GCP integration regression
# Tests hang waiting for Docker services that will never be available
```

#### 2. Missing Alternative Validation Methods
**Issue:** No fallback validation for WebSocket functionality when Docker unavailable

## REMEDIATION IMPLEMENTATION PLAN

### PHASE 1: Core Docker Manager Timeout Enforcement

#### 1.1 Fix `_run_subprocess_safe` Timeout Handling
**File:** `/test_framework/unified_docker_manager.py`  
**Target:** Add explicit timeout to all Docker operations

```python
# IMPLEMENTATION FIX:
def _run_subprocess_safe(cmd, timeout=10, **kwargs):
    """Run subprocess with mandatory timeout enforcement."""
    import sys
    try:
        # CRITICAL: Enforce timeout for all Docker operations
        if 'timeout' not in kwargs:
            kwargs['timeout'] = timeout
        
        # Existing environment setup...
        if 'env' not in kwargs:
            kwargs['env'] = _get_safe_subprocess_env()
        
        # CRITICAL: Use subprocess.run with timeout
        return subprocess.run(cmd, timeout=timeout, **kwargs)
        
    except subprocess.TimeoutExpired as e:
        # CRITICAL: Handle timeout explicitly
        _get_logger().error(f"Docker command timed out after {timeout}s: {cmd}")
        # Return failed result with timeout indicator
        return subprocess.CompletedProcess(
            args=cmd, returncode=124, stdout="", stderr=f"Timeout after {timeout}s"
        )
    except Exception as e:
        # Existing error handling...
```

#### 1.2 Fix `wait_for_services` Timeout Logic
**File:** `/test_framework/unified_docker_manager.py`  
**Target:** Accurate timeout enforcement with early termination

```python
# IMPLEMENTATION FIX:
def wait_for_services(self, services: Optional[List[str]] = None, timeout: int = 60) -> bool:
    """Wait for services with strict timeout enforcement."""
    if services is None:
        services = list(self.SERVICES.keys())
    
    env_name = self._get_environment_name()
    start_time = time.time()
    
    _get_logger().info(f"⏳ Waiting for services (max {timeout}s): {', '.join(services)}")
    
    unhealthy_services = {}
    restart_attempts = {}
    max_restart_attempts = 2
    last_status_print = 0
    
    # CRITICAL: Check timeout before each iteration
    while True:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            _get_logger().error(f"⏰ Timeout after {elapsed:.2f}s (limit: {timeout}s)")
            return False
        
        all_healthy = True
        current_unhealthy = []
        
        # Check each service with individual timeout
        for service in services:
            # CRITICAL: Use remaining time for health check
            remaining_time = max(1, timeout - elapsed)
            is_healthy = self._is_service_healthy_with_timeout(env_name, service, remaining_time)
            
            if not is_healthy:
                all_healthy = False
                current_unhealthy.append(service)
                
                # Track unhealthy duration
                if service not in unhealthy_services:
                    unhealthy_services[service] = time.time()
                    _get_logger().warning(f"⚠️ Service {service} is unhealthy")
            else:
                # Service recovered
                if service in unhealthy_services:
                    duration = time.time() - unhealthy_services[service]
                    _get_logger().info(f"✅ Service {service} recovered after {duration:.1f}s")
                    unhealthy_services.pop(service, None)
                    restart_attempts.pop(service, None)
        
        # CRITICAL: Check timeout again before continuing
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            _get_logger().error(f"⏰ Timeout after {elapsed:.2f}s checking services")
            return False
        
        if all_healthy:
            _get_logger().info(f"✅ All services healthy after {elapsed:.2f}s")
            return True
        
        # CRITICAL: Adaptive sleep with timeout check
        remaining_time = timeout - elapsed
        sleep_time = min(2, remaining_time - 0.5)  # Leave 0.5s buffer
        if sleep_time > 0:
            time.sleep(sleep_time)
        else:
            # No time left for sleep, one final check
            break
    
    return False
```

#### 1.3 Add Fast Docker Availability Check
**File:** `/test_framework/unified_docker_manager.py`  
**Target:** 2-second Docker daemon availability check

```python
# IMPLEMENTATION FIX:
def is_docker_available_fast(self, timeout: float = 2.0) -> bool:
    """Fast Docker availability check with strict timeout."""
    try:
        start_time = time.time()
        
        # CRITICAL: Quick Docker version check with timeout
        result = _run_subprocess_safe(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            timeout=timeout,
            capture_output=True,
            text=True
        )
        
        elapsed = time.time() - start_time
        
        if result.returncode == 0 and result.stdout.strip():
            _get_logger().info(f"✅ Docker available - checked in {elapsed:.2f}s")
            return True
        else:
            _get_logger().warning(f"❌ Docker not available - returncode: {result.returncode}")
            return False
            
    except Exception as e:
        _get_logger().warning(f"❌ Docker availability check failed: {e}")
        return False
```

### PHASE 2: WebSocket Test Graceful Degradation

#### 2.1 Docker-Aware Test Decorator
**File:** `/tests/mission_critical/websocket_real_test_base.py`  
**Target:** Smart Docker requirement handling

```python
# IMPLEMENTATION FIX:
def require_docker_services_smart(fallback: str = "skip") -> callable:
    """Smart Docker services requirement with graceful degradation.
    
    Args:
        fallback: "skip" (default), "mock", or "fail"
    """
    def decorator(test_func):
        @functools.wraps(test_func)
        async def wrapper(*args, **kwargs):
            manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
            
            # CRITICAL: Fast availability check (2s timeout)
            if not manager.is_docker_available_fast(timeout=2.0):
                if fallback == "skip":
                    pytest.skip("Docker services not available - test requires real WebSocket connections")
                elif fallback == "fail":
                    pytest.fail("Docker services required but not available. Start Docker: docker compose up -d")
                elif fallback == "mock":
                    # FUTURE: Could implement lightweight WebSocket mock validation
                    pytest.skip("Docker unavailable, mock fallback not yet implemented")
                else:
                    pytest.fail(f"Invalid fallback mode: {fallback}")
            
            # Docker available, proceed with real test
            return await test_func(*args, **kwargs)
        return wrapper
    return decorator
```

#### 2.2 Update Mission Critical WebSocket Tests
**File:** `/tests/mission_critical/test_websocket_agent_events_suite.py`  
**Target:** Add Docker awareness with clear messaging

```python
# IMPLEMENTATION FIX:
class TestRealE2EWebSocketAgentFlow:
    """End-to-end tests using REAL services - graceful Docker handling."""
    
    @pytest.fixture(autouse=True)
    async def setup_real_e2e_environment(self):
        """Setup real E2E test environment with smart Docker handling."""
        # CRITICAL: Fast Docker check before test setup
        manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        if not manager.is_docker_available_fast(timeout=2.0):
            pytest.skip(
                "Docker not available for real WebSocket tests. "
                "To run mission critical tests: docker compose up -d"
            )
        
        # Docker available, create real test base
        self.test_base = WebSocketTestBase(
            config=RealWebSocketTestConfig(
                connection_timeout=20.0,
                event_timeout=15.0,
                docker_startup_timeout=30.0  # REDUCED from 120s
            ),
            require_real_connections=True
        )
        
        # CRITICAL: Fast service orchestration with timeout
        success = await self.test_base.setup_with_timeout(timeout=30)
        if not success:
            pytest.fail("Real WebSocket test environment setup failed within 30s timeout")

    @pytest.mark.asyncio
    @pytest.mark.critical
    @require_docker_services_smart(fallback="skip")
    async def test_agent_registry_websocket_manager_integration(self):
        """Test with Docker awareness and graceful degradation."""
        # Test implementation with timeout enforcement...
```

### PHASE 3: Developer Experience Improvements

#### 3.1 Enhanced Error Messages
**File:** `/test_framework/unified_docker_manager.py`  
**Target:** Clear guidance for developers

```python
# IMPLEMENTATION FIX:
def wait_for_services(self, services: Optional[List[str]] = None, timeout: int = 60) -> bool:
    """Wait for services with developer-friendly error messages."""
    # ... timeout logic ...
    
    # Enhanced timeout error with guidance
    if elapsed >= timeout:
        unhealthy_list = [s for s in services if s in current_unhealthy]
        
        error_msg = (
            f"⏰ Services not ready after {elapsed:.2f}s (limit: {timeout}s)\n"
            f"Unhealthy services: {', '.join(unhealthy_list)}\n"
            f"To fix: docker compose -f docker-compose.alpine-test.yml up -d\n"
            f"Check status: docker compose ps\n"
            f"View logs: docker compose logs {' '.join(unhealthy_list)}"
        )
        _get_logger().error(error_msg)
        return False
```

#### 3.2 Test Execution Guidance
**File:** `/tests/mission_critical/test_websocket_agent_events_suite.py`  
**Target:** Clear instructions for developers

```python
# IMPLEMENTATION FIX:
def pytest_configure(config):
    """Configure pytest with helpful Docker guidance."""
    manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
    
    if not manager.is_docker_available_fast(timeout=2.0):
        print("\n" + "="*80)
        print("🐳 DOCKER REQUIRED FOR MISSION CRITICAL WEBSOCKET TESTS")
        print("="*80)
        print("To run WebSocket tests that validate $500K+ ARR chat functionality:")
        print("1. Start Docker: docker compose -f docker-compose.alpine-test.yml up -d")
        print("2. Verify status: docker compose ps")
        print("3. Run tests: python tests/mission_critical/test_websocket_agent_events_suite.py")
        print("="*80 + "\n")
```

## VALIDATION CRITERIA

### Performance Targets
- **Docker timeout:** 13.48s → ≤ 10s (26% improvement minimum)  
- **WebSocket test feedback:** 120s+ → < 10s (92% improvement)
- **Docker availability check:** < 2s (new capability)
- **Mission critical test accessibility:** Blocked → Functional with clear messaging

### Functional Requirements
1. **Timeout Enforcement:** `wait_for_services(timeout=10)` must fail after exactly 10 seconds
2. **Fast Docker Detection:** `is_docker_available_fast()` completes in < 2s
3. **Graceful Degradation:** WebSocket tests skip gracefully when Docker unavailable
4. **Clear Error Messages:** Developers get actionable guidance for Docker issues
5. **Business Continuity:** Mission critical tests can run when Docker available

### Test Cases for Validation

#### 4.1 Timeout Enforcement Tests
```python
# TEST: timeout_enforcement_validation.py
def test_wait_for_services_timeout_precision():
    """Validate exact timeout enforcement."""
    manager = UnifiedDockerManager()
    start_time = time.time()
    
    # Test with unavailable services
    result = manager.wait_for_services(["nonexistent"], timeout=10)
    elapsed = time.time() - start_time
    
    assert not result, "Should fail for unavailable services"
    assert 9.5 <= elapsed <= 10.5, f"Expected ~10s, got {elapsed:.2f}s"

def test_docker_availability_fast_check():
    """Validate fast Docker availability check."""
    manager = UnifiedDockerManager()
    start_time = time.time()
    
    result = manager.is_docker_available_fast(timeout=2.0)
    elapsed = time.time() - start_time
    
    assert elapsed <= 2.5, f"Expected ≤2.5s, got {elapsed:.2f}s"
    assert isinstance(result, bool), "Should return boolean"
```

#### 4.2 WebSocket Test Graceful Degradation
```python
# TEST: websocket_graceful_degradation.py
@mock.patch('test_framework.unified_docker_manager.UnifiedDockerManager.is_docker_available_fast')
def test_websocket_test_docker_unavailable_skip(mock_docker_check):
    """Validate graceful skip when Docker unavailable."""
    mock_docker_check.return_value = False
    
    with pytest.raises(pytest.skip.Exception) as exc_info:
        # Should skip gracefully, not hang
        test_function_with_docker_requirement()
    
    assert "Docker not available" in str(exc_info.value)
```

## RISK ASSESSMENT

### Technical Risks
- **LOW:** Timeout logic changes are isolated to specific methods
- **LOW:** Existing functionality preserved with backward compatibility  
- **LOW:** Changes only affect error handling and timeout enforcement

### Business Risks
- **HIGH (Current):** Cannot validate $500K+ ARR chat functionality
- **LOW (After Fix):** Mission critical tests restored, chat validation enabled

### Implementation Risks
- **MITIGATION:** Implement changes incrementally with validation at each step
- **MITIGATION:** Maintain backward compatibility for existing test infrastructure  
- **MITIGATION:** Add comprehensive test coverage for new timeout logic

## SUCCESS METRICS

### Primary Success Criteria
1. **Mission Critical Test Restoration:** WebSocket tests run successfully in < 30s
2. **Timeout Precision:** Docker operations respect timeout parameters (±0.5s tolerance)
3. **Developer Experience:** Clear feedback within 10s when Docker unavailable
4. **Business Value:** Chat functionality validation unblocked

### Performance Improvements
- **Docker timeout accuracy:** 65% (from 35% overrun to ±5% tolerance)
- **Test feedback speed:** 92% improvement (120s+ → <10s)
- **Developer productivity:** Docker issues diagnosed in <2s vs 30s+

### Long-term Benefits
1. **Reliable CI/CD:** Mission critical tests no longer block pipeline
2. **Enhanced Development Velocity:** Fast feedback for Docker-related issues  
3. **Business Risk Mitigation:** Chat functionality validation restored
4. **Technical Debt Reduction:** Robust timeout handling across test infrastructure

## IMPLEMENTATION TIMELINE

### Phase 1: Core Fixes (Day 1)
- [ ] Implement `_run_subprocess_safe` timeout enforcement
- [ ] Fix `wait_for_services` timeout logic  
- [ ] Add `is_docker_available_fast` method
- [ ] Create timeout enforcement validation tests

### Phase 2: Test Infrastructure (Day 2)  
- [ ] Implement `require_docker_services_smart` decorator
- [ ] Update mission critical WebSocket tests with graceful degradation
- [ ] Add developer guidance and error messages
- [ ] Test graceful degradation scenarios

### Phase 3: Validation & Documentation (Day 3)
- [ ] Run comprehensive validation test suite
- [ ] Verify all success criteria met
- [ ] Update documentation and developer guides
- [ ] Validate business value: Chat functionality testing restored

## DEPLOYMENT PLAN

### Pre-Deployment Validation
1. **Unit Tests:** All timeout enforcement tests pass
2. **Integration Tests:** WebSocket tests run successfully with Docker
3. **Degradation Tests:** WebSocket tests skip gracefully without Docker  
4. **Performance Tests:** Timeout accuracy within ±0.5s tolerance

### Deployment Steps
1. **Deploy Core Fixes:** Update `UnifiedDockerManager` timeout logic
2. **Deploy Test Infrastructure:** Update WebSocket test base classes
3. **Deploy Mission Critical Tests:** Update WebSocket agent event tests
4. **Validate Success:** Run full mission critical test suite

### Post-Deployment Monitoring
1. **CI/CD Pipeline:** Monitor test execution times and success rates
2. **Developer Feedback:** Track Docker-related issue resolution time
3. **Business Metrics:** Validate chat functionality testing restored
4. **Performance Tracking:** Monitor timeout accuracy and test feedback speed

---

## CONCLUSION

This remediation plan addresses the root cause of GitHub issue #411 by implementing precise timeout enforcement in Docker operations and adding graceful degradation for WebSocket tests. The solution balances technical rigor with developer experience, ensuring mission critical tests can validate the $500K+ ARR chat functionality while providing clear guidance when Docker services are unavailable.

**Key Benefits:**
- **Business Value:** Chat functionality validation restored  
- **Developer Experience:** Fast feedback and clear error guidance
- **Technical Excellence:** Robust timeout handling and graceful degradation
- **Risk Mitigation:** Mission critical tests no longer block deployments

The implementation follows established patterns in the codebase while introducing minimal risk through isolated, well-tested changes to timeout logic and error handling.