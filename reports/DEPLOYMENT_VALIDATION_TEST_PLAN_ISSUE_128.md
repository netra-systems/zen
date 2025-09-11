# Issue #128 Deployment Validation Test Plan
# WebSocket Connectivity Remediation - Comprehensive Test Strategy

**Generated:** 2025-09-09 18:00:00  
**Issue:** #128 - P1 critical test failures: 92% to 100% pass rate target  
**Environment:** Staging GCP  
**Test Framework:** Non-Docker (Unit, Integration, E2E on staging remote)  
**Root Cause:** WebSocket connectivity timeouts due to staging infrastructure configuration  

## Executive Summary

This test plan validates that deploying the implemented WebSocket/infrastructure fixes will resolve the P1 critical test failures in issue #128. The plan consists of **failing tests that will PASS after deployment**, proving the deployment resolves the issue.

**Current State:**
- ✅ 23/25 P1 tests passing (92%)
- ❌ 2 failing tests: `test_023_streaming_partial_results_real` and `test_025_critical_event_delivery_real`
- **Root Cause:** WebSocket connection timeouts during `asyncio.selector.select()` blocking

**Implemented Fixes (Ready for Deployment):**
- WebSocket timeout configurations (60% reduction: 15min → 6min)
- Cloud Run resource scaling (4Gi memory, 4 CPU cores)
- Circuit breaker patterns with exponential backoff
- asyncio.selector.select() blocking optimizations
- Progressive timeout patterns for Windows/Cloud environments

---

## Phase 1: Pre-Deployment Validation Tests
### Purpose: Confirm current failure state and that fixes exist in codebase but are not active

### 1.1 Current P1 Failure State Confirmation

**Test Command:**
```bash
# Confirm the 2 failing tests still fail
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_streaming_partial_results_real -v --tb=short --timeout=120
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_critical_event_delivery_real -v --tb=short --timeout=60
```

**Expected Result:** ❌ BOTH tests MUST fail with timeout errors (proving deployment gap exists)
- `test_023`: Timeout after 120 seconds during WebSocket connection
- `test_025`: Timeout after 60 seconds during WebSocket connection
- Stack trace shows: `asyncio.selector.select()` blocking

### 1.2 WebSocket Timeout Configuration Gap Validation 

**Test File:** `tests/unit/deployment_validation/test_websocket_timeout_config_gap.py`
```python
"""
Unit test to validate WebSocket timeout configurations exist in codebase but are not active in staging
"""
import pytest
from netra_backend.app.websocket_core.circuit_breaker import CircuitBreakerConfig
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager

class TestWebSocketTimeoutConfigurationGap:
    
    def test_websocket_timeout_configs_exist_in_codebase(self):
        """UNIT: Validate timeout configs exist in deployment script"""
        # This test reads the deploy script and confirms optimized timeouts exist
        deploy_script_path = "scripts/deploy_to_gcp.py"
        with open(deploy_script_path, 'r') as f:
            content = f.read()
        
        # MUST find these Issue #128 optimized timeout values
        assert 'WEBSOCKET_CONNECTION_TIMEOUT": "360"' in content, "6-minute timeout not found in deploy script"
        assert 'WEBSOCKET_HEARTBEAT_INTERVAL": "15"' in content, "15s heartbeat not found in deploy script"
        assert 'WEBSOCKET_HEARTBEAT_TIMEOUT": "45"' in content, "45s heartbeat timeout not found in deploy script"
        assert 'backend_memory = "4Gi"' in content, "4Gi memory scaling not found in deploy script"
        assert 'backend_cpu = "4"' in content, "4 CPU scaling not found in deploy script"
        
    def test_circuit_breaker_implementation_exists(self):
        """UNIT: Validate circuit breaker implementation exists"""
        # This test imports and validates the circuit breaker exists
        config = CircuitBreakerConfig()
        assert config.failure_threshold > 0, "Circuit breaker not properly implemented"
        assert config.max_retry_attempts == 5, "Max retry attempts not configured for Issue #128"
        
    def test_current_staging_environment_lacks_optimized_timeouts(self):
        """INTEGRATION: Validate current staging lacks optimized timeout configs"""
        # This test should FAIL before deployment, PASS after deployment
        # It attempts to validate that staging has the optimized timeout values
        
        import requests
        import os
        
        # This test EXPECTS TO FAIL before deployment
        # After deployment, staging should have these environment variables active
        staging_backend_url = "https://netra-backend-staging-00282-244513.a.run.app"
        
        try:
            # Attempt to get health endpoint that would show timeout configs
            response = requests.get(f"{staging_backend_url}/health", timeout=10)
            health_data = response.json()
            
            # Check if optimized timeout configs are active (will be False before deployment)
            websocket_timeout = health_data.get("config", {}).get("websocket_connection_timeout")
            
            # BEFORE DEPLOYMENT: This assertion SHOULD FAIL (configs not active)
            # AFTER DEPLOYMENT: This assertion SHOULD PASS (configs active)
            assert websocket_timeout == "360", f"Optimized WebSocket timeout not active in staging: {websocket_timeout}"
            
        except (AssertionError, KeyError):
            # Expected before deployment - optimized configs not yet active
            pytest.fail("EXPECTED FAILURE: Optimized WebSocket timeout configs not yet deployed to staging")
```

**Test Command:**
```bash
python -m pytest tests/unit/deployment_validation/test_websocket_timeout_config_gap.py -v
```

**Expected Result:** 
- ✅ First 2 tests PASS (fixes exist in codebase)
- ❌ Third test FAILS (staging lacks optimized configs) - **PROVES DEPLOYMENT NEEDED**

### 1.3 Staging WebSocket Connection Baseline Test

**Test File:** `tests/integration/deployment_validation/test_staging_websocket_baseline.py`
```python
"""
Integration test to establish baseline WebSocket connection performance before deployment
"""
import pytest
import asyncio
import time
import websockets
from tests.e2e.staging_test_config import get_staging_config

class TestStagingWebSocketBaseline:
    
    @pytest.mark.asyncio
    async def test_staging_websocket_connection_timeout_baseline(self):
        """INTEGRATION: Measure current WebSocket connection timeout behavior"""
        config = get_staging_config()
        ws_headers = config.get_websocket_headers()
        
        start_time = time.time()
        connection_successful = False
        timeout_occurred = False
        
        # BEFORE DEPLOYMENT: This should timeout/fail frequently
        # AFTER DEPLOYMENT: This should succeed more reliably
        try:
            async with websockets.connect(
                config.websocket_url,
                additional_headers=ws_headers,
                subprotocols=["jwt-auth"],
                close_timeout=10
            ) as ws:
                # Wait for welcome message - this is where timeouts occur
                welcome_response = await asyncio.wait_for(ws.recv(), timeout=30)
                connection_successful = True
                
        except asyncio.TimeoutError:
            timeout_occurred = True
            duration = time.time() - start_time
            print(f"WebSocket connection timeout after {duration:.2f}s")
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"WebSocket connection error after {duration:.2f}s: {e}")
        
        # BEFORE DEPLOYMENT: High probability of timeout (this test documents current state)
        # AFTER DEPLOYMENT: Should succeed due to optimized timeouts
        
        # Log the current state for comparison after deployment
        duration = time.time() - start_time
        print(f"Baseline WebSocket connection attempt: {duration:.2f}s, Success: {connection_successful}, Timeout: {timeout_occurred}")
        
        # This test documents current behavior - failure is expected before deployment
        if timeout_occurred:
            pytest.fail(f"BASELINE: WebSocket connection timeout occurred after {duration:.2f}s (expected before deployment)")
```

**Test Command:**
```bash
python -m pytest tests/integration/deployment_validation/test_staging_websocket_baseline.py -v
```

**Expected Result:** ❌ FAILS with timeout (documents current poor performance before deployment)

---

## Phase 2: Deployment Readiness Tests
### Purpose: Validate that fixes are properly configured and ready for deployment

### 2.1 WebSocket Circuit Breaker Readiness Test

**Test File:** `tests/unit/deployment_validation/test_circuit_breaker_readiness.py`
```python
"""
Unit test to validate circuit breaker implementation is ready for deployment
"""
import pytest
from netra_backend.app.websocket_core.circuit_breaker import WebSocketCircuitBreaker, CircuitBreakerConfig

class TestCircuitBreakerReadiness:
    
    def test_circuit_breaker_staging_configuration(self):
        """UNIT: Validate staging-optimized circuit breaker configuration"""
        # Create staging-specific configuration (from Issue #128 implementation)
        staging_config = CircuitBreakerConfig(
            failure_threshold=3,       # Open circuit after 3 failures (aggressive for staging)
            recovery_timeout=15,       # Try recovery after 15s
            max_retry_attempts=5,      # Maximum retry attempts
            base_delay=0.5,           # Start with 0.5s delay  
            max_delay=30.0,           # Cap at 30s delay
            timeout=10.0              # 10s timeout for staging connections
        )
        
        circuit_breaker = WebSocketCircuitBreaker(config=staging_config)
        assert circuit_breaker.config.failure_threshold == 3
        assert circuit_breaker.config.max_retry_attempts == 5
        assert circuit_breaker.config.timeout == 10.0
        
    def test_circuit_breaker_exponential_backoff_pattern(self):
        """UNIT: Validate exponential backoff retry logic"""
        config = CircuitBreakerConfig(base_delay=0.5, max_delay=30.0, max_retry_attempts=5)
        circuit_breaker = WebSocketCircuitBreaker(config=config)
        
        # Test exponential backoff calculation
        delays = []
        for attempt in range(5):
            delay = circuit_breaker._calculate_backoff_delay(attempt)
            delays.append(delay)
            assert delay >= config.base_delay
            assert delay <= config.max_delay
        
        # Verify delays increase exponentially (until max_delay cap)
        assert delays[0] < delays[1] < delays[2]
        print(f"Backoff delays: {delays}")
        
    def test_circuit_breaker_integration_ready(self):
        """UNIT: Validate circuit breaker can be integrated with WebSocket connections"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=5)
        circuit_breaker = WebSocketCircuitBreaker(config=config)
        
        # Simulate failures to open circuit
        for i in range(3):
            circuit_breaker.record_failure()
        
        assert circuit_breaker.is_open(), "Circuit should be open after threshold failures"
        
        # Simulate time passage for recovery
        import time
        circuit_breaker._last_failure_time = time.time() - 10  # 10s ago
        assert circuit_breaker.can_attempt_request(), "Circuit should allow recovery attempt"
```

**Test Command:**
```bash
python -m pytest tests/unit/deployment_validation/test_circuit_breaker_readiness.py -v
```

**Expected Result:** ✅ ALL tests PASS (circuit breaker implementation ready)

### 2.2 GCP Deployment Configuration Validation Test

**Test File:** `tests/unit/deployment_validation/test_gcp_deployment_config.py`
```python
"""
Unit test to validate GCP deployment configuration is optimized for Issue #128
"""
import pytest
import os
import subprocess

class TestGCPDeploymentConfiguration:
    
    def test_deploy_script_timeout_optimizations(self):
        """UNIT: Validate deploy script contains Issue #128 timeout optimizations"""
        deploy_script = "scripts/deploy_to_gcp.py"
        
        with open(deploy_script, 'r') as f:
            content = f.read()
        
        # Validate all Issue #128 timeout optimizations are present
        optimizations = {
            "WEBSOCKET_CONNECTION_TIMEOUT": "360",  # 6 minutes (60% reduction)
            "WEBSOCKET_HEARTBEAT_INTERVAL": "15",   # 15s heartbeat
            "WEBSOCKET_HEARTBEAT_TIMEOUT": "45",    # 45s heartbeat timeout
            "WEBSOCKET_CLEANUP_INTERVAL": "120",    # 2 minute cleanup
            "WEBSOCKET_CONNECT_TIMEOUT": "10",      # 10s initial connection
            "WEBSOCKET_HANDSHAKE_TIMEOUT": "15",    # 15s handshake
            "WEBSOCKET_PING_TIMEOUT": "5",          # 5s ping timeout
            "WEBSOCKET_CLOSE_TIMEOUT": "10"         # 10s close timeout
        }
        
        for env_var, expected_value in optimizations.items():
            expected_line = f'"{env_var}": "{expected_value}"'
            assert expected_line in content, f"Missing timeout optimization: {env_var}={expected_value}"
        
        print("✅ All Issue #128 WebSocket timeout optimizations found in deploy script")
        
    def test_cloud_run_resource_scaling(self):
        """UNIT: Validate Cloud Run resource scaling for WebSocket reliability"""
        deploy_script = "scripts/deploy_to_gcp.py"
        
        with open(deploy_script, 'r') as f:
            content = f.read()
        
        # Validate Issue #128 resource scaling
        assert 'backend_memory = "4Gi"' in content, "4Gi memory scaling not configured"
        assert 'backend_cpu = "4"' in content, "4 CPU scaling not configured"
        assert '# ISSUE #128 FIX' in content, "Issue #128 fix markers not found"
        
        print("✅ Cloud Run resource scaling optimizations found in deploy script")
        
    def test_deployment_command_validity(self):
        """UNIT: Validate deployment command syntax"""
        # Test that the deploy script has valid Python syntax
        deploy_script = "scripts/deploy_to_gcp.py"
        
        try:
            with open(deploy_script, 'r') as f:
                code = compile(f.read(), deploy_script, 'exec')
            print("✅ Deploy script has valid Python syntax")
        except SyntaxError as e:
            pytest.fail(f"Deploy script has syntax error: {e}")
```

**Test Command:**
```bash
python -m pytest tests/unit/deployment_validation/test_gcp_deployment_config.py -v
```

**Expected Result:** ✅ ALL tests PASS (deployment configuration ready)

### 2.3 Asyncio Selector Optimization Validation Test

**Test File:** `tests/unit/deployment_validation/test_asyncio_selector_optimization.py`
```python
"""
Unit test to validate asyncio.selector.select() optimizations are implemented
"""
import pytest
from netra_backend.app.core.windows_asyncio_safe import timeout_select, windows_safe_wait_for

class TestAsyncioSelectorOptimization:
    
    def test_selector_timeout_optimization_exists(self):
        """UNIT: Validate selector.select() timeout limiting exists"""
        # Test that timeout_select limits selector timeout to prevent indefinite blocking
        
        # Test with None timeout (should be limited to 1.0s)
        limited_timeout = timeout_select(None)
        assert limited_timeout <= 1.0, f"Selector timeout not limited: {limited_timeout}"
        
        # Test with large timeout (should be limited to 1.0s)  
        limited_timeout = timeout_select(300.0)
        assert limited_timeout <= 1.0, f"Large timeout not limited: {limited_timeout}"
        
        # Test with small timeout (should pass through)
        limited_timeout = timeout_select(0.5)
        assert limited_timeout == 0.5, f"Small timeout modified: {limited_timeout}"
        
        print("✅ Selector timeout optimization working correctly")
        
    def test_windows_safe_patterns_cloud_compatible(self):
        """UNIT: Validate Windows-safe patterns work in cloud environments"""
        import asyncio
        
        # Test windows_safe_wait_for doesn't cause deadlocks
        async def test_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        # This should not deadlock (Issue #128 fix)
        async def run_test():
            try:
                result = await windows_safe_wait_for(test_operation(), timeout=1.0)
                assert result == "success"
                return True
            except asyncio.TimeoutError:
                return False
        
        # Run the test synchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            success = loop.run_until_complete(run_test())
            assert success, "windows_safe_wait_for failed to complete operation"
            print("✅ Windows-safe asyncio patterns working correctly")
        finally:
            loop.close()
            
    def test_cloud_environment_detection(self):
        """UNIT: Validate cloud environment detection for selector optimizations"""
        from netra_backend.app.core.windows_asyncio_safe import is_cloud_environment
        
        # Test cloud environment detection logic
        # Note: This may vary based on actual environment
        cloud_detected = is_cloud_environment()
        print(f"Cloud environment detected: {cloud_detected}")
        
        # The detection should work without errors
        assert isinstance(cloud_detected, bool), "Cloud detection should return boolean"
        
        print("✅ Cloud environment detection functioning")
```

**Test Command:**
```bash
python -m pytest tests/unit/deployment_validation/test_asyncio_selector_optimization.py -v
```

**Expected Result:** ✅ ALL tests PASS (asyncio optimizations ready)

---

## Phase 3: Post-Deployment Validation Plan
### Purpose: Validate that deployment successfully activates the fixes and resolves P1 failures

### 3.1 P1 Critical Tests Validation (The Main Event)

**Test Command:**
```bash
# AFTER DEPLOYMENT: These should now PASS
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_streaming_partial_results_real -v --tb=short --timeout=120
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_critical_event_delivery_real -v --tb=short --timeout=60

# Full P1 suite validation  
python -m pytest tests/e2e/staging/test_priority1_critical.py -v --tb=short
```

**Expected Result:** ✅ BOTH previously failing tests now PASS
- `test_023`: Completes successfully within timeout due to optimized WebSocket configs
- `test_025`: Completes successfully within timeout due to circuit breaker patterns
- **Overall P1 Pass Rate: 100% (25/25 tests passing)**

### 3.2 WebSocket Connection Performance Validation

**Test File:** `tests/integration/deployment_validation/test_websocket_performance_post_deployment.py`
```python
"""
Integration test to validate WebSocket connection performance after deployment
"""
import pytest
import asyncio
import time
import websockets
from tests.e2e.staging_test_config import get_staging_config

class TestWebSocketPerformancePostDeployment:
    
    @pytest.mark.asyncio
    async def test_websocket_connection_performance_improved(self):
        """INTEGRATION: Validate WebSocket connection performance after deployment"""
        config = get_staging_config()
        ws_headers = config.get_websocket_headers()
        
        connection_times = []
        success_count = 0
        
        # Test multiple connections to validate consistency
        for attempt in range(5):
            start_time = time.time()
            try:
                async with websockets.connect(
                    config.websocket_url,
                    additional_headers=ws_headers,
                    subprotocols=["jwt-auth"],
                    close_timeout=10
                ) as ws:
                    # Wait for welcome message
                    welcome_response = await asyncio.wait_for(ws.recv(), timeout=30)
                    connection_time = time.time() - start_time
                    connection_times.append(connection_time)
                    success_count += 1
                    print(f"Connection {attempt + 1}: {connection_time:.2f}s - SUCCESS")
                    
            except Exception as e:
                connection_time = time.time() - start_time
                connection_times.append(connection_time)
                print(f"Connection {attempt + 1}: {connection_time:.2f}s - FAILED: {e}")
        
        # AFTER DEPLOYMENT: Should have much better performance
        avg_connection_time = sum(connection_times) / len(connection_times)
        success_rate = success_count / 5
        
        print(f"Average connection time: {avg_connection_time:.2f}s")
        print(f"Success rate: {success_rate * 100:.1f}% ({success_count}/5)")
        
        # Validate improvements from Issue #128 fixes
        assert avg_connection_time < 10.0, f"Average connection time too slow: {avg_connection_time:.2f}s"
        assert success_rate >= 0.8, f"Success rate too low: {success_rate * 100:.1f}%"
        
        print("✅ WebSocket connection performance significantly improved after deployment")
        
    @pytest.mark.asyncio
    async def test_websocket_timeout_configs_active(self):
        """INTEGRATION: Validate optimized timeout configs are active in staging"""
        import httpx
        
        config = get_staging_config()
        
        # Check if optimized timeout configs are now active
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{config.backend_url}/health")
            health_data = response.json()
            
            # These should now be active after deployment
            config_data = health_data.get("config", {})
            
            # Validate Issue #128 timeout optimizations are active
            expected_timeouts = {
                "websocket_connection_timeout": "360",
                "websocket_heartbeat_interval": "15", 
                "websocket_heartbeat_timeout": "45"
            }
            
            for config_key, expected_value in expected_timeouts.items():
                actual_value = config_data.get(config_key)
                assert actual_value == expected_value, f"Timeout config not active: {config_key}={actual_value}, expected={expected_value}"
            
            print("✅ All Issue #128 timeout optimizations are active in staging")
```

**Test Command:**
```bash
python -m pytest tests/integration/deployment_validation/test_websocket_performance_post_deployment.py -v
```

**Expected Result:** ✅ ALL tests PASS (performance dramatically improved)

### 3.3 System Stability Regression Test

**Test Command:**
```bash
# Validate that the deployment doesn't break existing functionality
python -m pytest tests/e2e/staging/test_priority1_critical.py -v --tb=short
python -m pytest tests/integration/golden_path/test_complete_golden_path_business_value.py -v --tb=short
```

**Expected Result:** ✅ ALL tests PASS (no regressions introduced)

---

## Test Execution Commands Summary

### Phase 1: Pre-Deployment (Should Fail - Proving Need)
```bash
# Create test files first
mkdir -p tests/unit/deployment_validation tests/integration/deployment_validation

# Run pre-deployment validation (expects failures)
python -m pytest tests/unit/deployment_validation/test_websocket_timeout_config_gap.py -v
python -m pytest tests/integration/deployment_validation/test_staging_websocket_baseline.py -v

# Confirm P1 failures still exist
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_streaming_partial_results_real -v --timeout=120
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_critical_event_delivery_real -v --timeout=60
```

### Phase 2: Deployment Readiness (Should Pass - Ready to Deploy)
```bash
python -m pytest tests/unit/deployment_validation/test_circuit_breaker_readiness.py -v
python -m pytest tests/unit/deployment_validation/test_gcp_deployment_config.py -v  
python -m pytest tests/unit/deployment_validation/test_asyncio_selector_optimization.py -v
```

### Phase 3: Post-Deployment (Should Pass - Fixes Active)
```bash
# THE CRITICAL TEST: P1 failures should now pass
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_streaming_partial_results_real -v --timeout=120
python -m pytest tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_critical_event_delivery_real -v --timeout=60

# Full validation
python -m pytest tests/e2e/staging/test_priority1_critical.py -v
python -m pytest tests/integration/deployment_validation/test_websocket_performance_post_deployment.py -v
```

## Success Criteria

### Before Deployment (Phase 1):
- ❌ 2/6 tests failing (P1 tests + config gap test)
- ❌ WebSocket timeouts occurring frequently
- ❌ Current staging lacks optimized configurations

### After Deployment (Phase 3):
- ✅ **100% P1 pass rate (25/25 tests)**
- ✅ `test_023_streaming_partial_results_real` passes consistently
- ✅ `test_025_critical_event_delivery_real` passes consistently  
- ✅ WebSocket connection time < 10 seconds average
- ✅ WebSocket connection success rate > 80%
- ✅ No system regressions

## Deployment Command

```bash
# Deploy the fixes to staging
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

## Business Impact Validation

**Before:** 92% P1 pass rate - 2 critical WebSocket tests failing due to infrastructure timeouts  
**After:** 100% P1 pass rate - All critical WebSocket functionality working reliably

**Risk Mitigation:** All fixes are infrastructure/configuration changes, not business logic changes, minimizing risk of functional regressions.

---

*This test plan provides a comprehensive validation strategy that will definitively prove whether deploying the Issue #128 fixes resolves the P1 critical test failures.*