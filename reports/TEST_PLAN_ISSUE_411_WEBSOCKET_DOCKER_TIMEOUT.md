# Test Plan: Issue #411 - WebSocket Test Suite Docker Timeout

## Impact
**CRITICAL**: Mission critical WebSocket test suite hangs for 120 seconds when Docker daemon unavailable, blocking validation of WebSocket events that deliver 90% of platform value ($500K+ ARR).

## Root Cause Analysis
- **Primary Issue**: `test_websocket_agent_events_suite.py` performs Docker availability checks with 30-second timeouts in rate limiter
- **Cascading Failure**: Multiple Docker commands attempted before fast-fail, causing cumulative 120+ second hangs
- **Business Impact**: Prevents validation of critical WebSocket agent events that enable substantive chat functionality

## Test Plan Overview

### Test Categories

#### 1. REPRODUCE THE ISSUE (Failing Tests)
Tests that demonstrate the current hanging behavior and validate our understanding of the problem.

#### 2. VALIDATE THE FIX (Passing Tests After Implementation)  
Tests that validate the Docker availability detection and fast-fail mechanisms work correctly.

---

## 1. FAILING TESTS - Reproduce Current Issue

### 1.1 Docker Availability Detection Timeout Test

**File**: `tests/unit/test_docker_availability_timeout_issue411.py`

```python
"""Test to reproduce Docker availability timeout issue #411."""

import time
import pytest
from unittest.mock import patch, MagicMock
from test_framework.unified_docker_manager import UnifiedDockerManager
from test_framework.docker_rate_limiter import DockerRateLimiter


class TestDockerAvailabilityTimeout:
    """Reproduce Docker availability timeout behavior."""
    
    def test_docker_availability_check_timeout_reproduction(self):
        """Reproduce 30-second timeout when Docker daemon unavailable."""
        start_time = time.time()
        
        with patch('subprocess.run') as mock_run:
            # Simulate Docker daemon not available (timeout)
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=['docker', '--version'], 
                timeout=5
            )
            
            manager = UnifiedDockerManager()
            result = manager.is_docker_available()
            
            duration = time.time() - start_time
            
            # This test SHOULD FAIL initially - demonstrating the timeout issue
            assert duration < 10, f"Docker availability check took {duration:.1f}s, expected < 10s fast-fail"
            assert result is False
    
    def test_websocket_test_suite_hanging_behavior(self):
        """Reproduce WebSocket test suite hanging behavior when Docker unavailable."""
        start_time = time.time()
        
        with patch('test_framework.unified_docker_manager.UnifiedDockerManager.is_docker_available') as mock_available:
            # Simulate Docker operations taking too long
            def slow_docker_check():
                time.sleep(30)  # Simulate 30s timeout
                return False
            
            mock_available.side_effect = slow_docker_check
            
            from tests.mission_critical.websocket_real_test_base import require_docker_services
            
            # This test SHOULD FAIL initially - demonstrating hanging behavior  
            with pytest.raises(pytest.fail.Exception):
                require_docker_services()
            
            duration = time.time() - start_time
            
            # This assertion will fail, proving the hanging issue exists
            assert duration < 5, f"require_docker_services took {duration:.1f}s, expected immediate failure"
```

**Expected Behavior**: This test FAILS, proving the hanging issue exists.

### 1.2 Rate Limiter Cumulative Timeout Test

**File**: `tests/unit/test_rate_limiter_cumulative_timeout_issue411.py`

```python
"""Test rate limiter cumulative timeout behavior."""

import time
import subprocess
from test_framework.docker_rate_limiter import DockerRateLimiter


class TestRateLimiterCumulativeTimeout:
    """Test cumulative timeout effects in Docker rate limiter."""
    
    def test_multiple_docker_commands_cumulative_timeout(self):
        """Demonstrate cumulative timeout when multiple Docker commands fail."""
        rate_limiter = DockerRateLimiter(max_retries=3)
        start_time = time.time()
        
        with patch('subprocess.run') as mock_run:
            # Simulate each Docker command timing out after 30 seconds
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=['docker', 'ps'], 
                timeout=30
            )
            
            # Try multiple commands that would be run during WebSocket test setup
            commands = [
                ['docker', '--version'],
                ['docker', 'ps'],
                ['docker', 'network', 'ls'],
                ['docker', 'compose', 'ps']
            ]
            
            for cmd in commands:
                try:
                    rate_limiter.execute_docker_command(cmd, timeout=30)
                except Exception:
                    pass  # Expected to fail
            
            duration = time.time() - start_time
            
            # This test SHOULD FAIL - showing cumulative timeout > 120s
            assert duration < 60, f"Cumulative Docker operations took {duration:.1f}s, expected < 60s with fast-fail"
```

**Expected Behavior**: This test FAILS, proving cumulative timeouts cause 120+ second hangs.

---

## 2. VALIDATION TESTS - Validate Fix Implementation

### 2.1 Fast Docker Availability Detection

**File**: `tests/unit/test_fast_docker_availability_issue411.py`

```python
"""Test fast Docker availability detection after fix."""

import time
import subprocess
from test_framework.unified_docker_manager import UnifiedDockerManager


class TestFastDockerAvailability:
    """Test Docker availability detection is fast and reliable."""
    
    def test_docker_availability_fast_fail_when_unavailable(self):
        """Test Docker availability check fails fast when daemon unavailable."""
        start_time = time.time()
        
        with patch('subprocess.run') as mock_run:
            # Simulate Docker daemon unavailable
            mock_run.side_effect = FileNotFoundError("docker: command not found")
            
            manager = UnifiedDockerManager()
            result = manager.is_docker_available()
            
            duration = time.time() - start_time
            
            # After fix: should be immediate
            assert duration < 1, f"Docker availability check took {duration:.1f}s, expected < 1s"
            assert result is False
    
    def test_docker_availability_timeout_handling(self):
        """Test Docker availability handles timeouts gracefully."""
        start_time = time.time()
        
        with patch('subprocess.run') as mock_run:
            # Simulate timeout but with reduced timeout value
            mock_run.side_effect = subprocess.TimeoutExpired(
                cmd=['docker', '--version'], 
                timeout=2  # Reduced from 30s to 2s
            )
            
            manager = UnifiedDockerManager()
            result = manager.is_docker_available()
            
            duration = time.time() - start_time
            
            # Should timeout quickly and return False
            assert duration < 5, f"Docker availability with timeout took {duration:.1f}s, expected < 5s"
            assert result is False
    
    def test_docker_availability_caching(self):
        """Test Docker availability result is cached for performance."""
        manager = UnifiedDockerManager()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # First call
            start_time = time.time()
            result1 = manager.is_docker_available()
            first_duration = time.time() - start_time
            
            # Second call should be cached
            start_time = time.time()
            result2 = manager.is_docker_available()
            second_duration = time.time() - start_time
            
            assert result1 is True
            assert result2 is True
            assert second_duration < first_duration / 10, "Second call should be much faster (cached)"
```

### 2.2 WebSocket Test Graceful Degradation

**File**: `tests/integration/test_websocket_docker_graceful_degradation_issue411.py`

```python
"""Test WebSocket tests handle Docker unavailability gracefully."""

import pytest
from tests.mission_critical.websocket_real_test_base import require_docker_services


class TestWebSocketDockerGracefulDegradation:
    """Test WebSocket infrastructure handles Docker unavailability."""
    
    def test_require_docker_services_fast_fail(self):
        """Test require_docker_services fails fast when Docker unavailable."""
        start_time = time.time()
        
        with patch('test_framework.unified_docker_manager.UnifiedDockerManager.is_docker_available', return_value=False):
            with pytest.raises(pytest.fail.Exception) as exc_info:
                require_docker_services()
            
            duration = time.time() - start_time
            
            # Should fail immediately, not after timeout
            assert duration < 2, f"require_docker_services took {duration:.1f}s, expected immediate failure"
            assert "Docker services required but not available" in str(exc_info.value)
    
    def test_websocket_test_base_docker_unavailable_handling(self):
        """Test WebSocket test base handles Docker unavailability gracefully."""
        from tests.mission_critical.websocket_real_test_base import RealWebSocketTestBase
        
        with patch('test_framework.unified_docker_manager.UnifiedDockerManager.is_docker_available', return_value=False):
            # Should either skip tests or fail fast, not hang
            start_time = time.time()
            
            try:
                test_base = RealWebSocketTestBase()
                # Attempt setup that would normally require Docker
                test_base.setup_method(None)
            except (pytest.skip.Exception, pytest.fail.Exception, RuntimeError):
                pass  # Expected behavior
            
            duration = time.time() - start_time
            assert duration < 5, f"WebSocket test base setup took {duration:.1f}s, expected fast failure/skip"
```

### 2.3 Alternative WebSocket Validation Methods

**File**: `tests/e2e/test_websocket_staging_validation_issue411.py`

```python
"""Test alternative WebSocket validation methods when Docker unavailable."""

import pytest
from shared.isolated_environment import get_env


class TestWebSocketStagingValidation:
    """Test WebSocket validation using staging environment when Docker unavailable."""
    
    @pytest.mark.skipif(
        not get_env().get("STAGING_WEBSOCKET_URL"),
        reason="Staging WebSocket URL not available"
    )
    def test_websocket_events_staging_validation(self):
        """Test WebSocket events using staging environment instead of local Docker."""
        # This test runs against staging when Docker is unavailable locally
        from test_framework.websocket_helpers import WebSocketTestHelpers
        
        staging_url = get_env().get("STAGING_WEBSOCKET_URL")
        
        # Test real WebSocket connection to staging
        helper = WebSocketTestHelpers()
        
        async def validate_staging_websocket():
            connection = await helper.create_staging_websocket_connection(staging_url)
            
            # Validate basic connectivity
            assert connection is not None
            
            # Send test message and verify response
            await connection.send_json({"type": "ping"})
            response = await connection.receive_json(timeout=10)
            
            assert response["type"] == "pong"
            
            await connection.close()
        
        # Run async test
        import asyncio
        asyncio.run(validate_staging_websocket())
    
    def test_websocket_test_mode_detection(self):
        """Test WebSocket test infrastructure detects appropriate test mode."""
        from test_framework.unified_docker_manager import UnifiedDockerManager, ServiceMode
        
        manager = UnifiedDockerManager()
        
        # When Docker unavailable, should default to staging/local mode
        with patch.object(manager, 'is_docker_available', return_value=False):
            effective_mode = manager.get_effective_mode(ServiceMode.DOCKER)
            
            # Should fallback to local mode instead of hanging
            assert effective_mode == ServiceMode.LOCAL
            
        # When Docker available, should use Docker mode
        with patch.object(manager, 'is_docker_available', return_value=True):
            effective_mode = manager.get_effective_mode(ServiceMode.DOCKER)
            assert effective_mode == ServiceMode.DOCKER
```

---

## 3. TEST EXECUTION STRATEGY

### 3.1 Test Environment Setup

**Prerequisites**:
- Python environment with test dependencies
- Access to staging environment (for alternative validation)
- NO Docker daemon (to test failure scenarios)

### 3.2 Execution Order

1. **Failing Tests First**: Run failing tests to confirm issue reproduction
2. **Fix Implementation**: Implement Docker availability fast-fail
3. **Validation Tests**: Run validation tests to confirm fix works
4. **Integration Validation**: Test full WebSocket test suite with fixes

### 3.3 Test Commands

```bash
# 1. Reproduce the issue (these should FAIL initially)
python -m pytest tests/unit/test_docker_availability_timeout_issue411.py -v
python -m pytest tests/unit/test_rate_limiter_cumulative_timeout_issue411.py -v

# 2. After implementing fix, validate solution
python -m pytest tests/unit/test_fast_docker_availability_issue411.py -v
python -m pytest tests/integration/test_websocket_docker_graceful_degradation_issue411.py -v

# 3. Test alternative validation methods
python -m pytest tests/e2e/test_websocket_staging_validation_issue411.py -v

# 4. Validate full WebSocket test suite no longer hangs
timeout 30 python tests/mission_critical/test_websocket_agent_events_suite.py
```

---

## 4. VALIDATION CRITERIA

### 4.1 Success Metrics

**Before Fix (Expected Failures)**:
- Docker availability checks take 30+ seconds when Docker unavailable
- Multiple Docker commands cause cumulative 120+ second hangs
- WebSocket test suite hangs instead of failing fast

**After Fix (Expected Passes)**:
- Docker availability checks complete within 2 seconds
- WebSocket test suite fails immediately (< 5 seconds) when Docker unavailable
- Alternative validation methods work with staging environment
- No cumulative timeout issues in Docker operations

### 4.2 Performance Benchmarks

| Scenario | Before Fix | After Fix | Improvement |
|----------|------------|-----------|-------------|
| Docker availability check (unavailable) | 30+ seconds | < 2 seconds | 93%+ faster |
| WebSocket test suite fail (no Docker) | 120+ seconds | < 5 seconds | 95%+ faster |
| Multiple Docker command failures | 120+ seconds | < 10 seconds | 91%+ faster |

### 4.3 Business Value Validation

- **Developer Productivity**: No more 2+ minute waits when Docker unavailable
- **CI/CD Pipeline**: Faster feedback loops in environments without Docker
- **WebSocket Event Validation**: Alternative methods ensure critical business functionality still tested
- **Platform Reliability**: Critical $500K+ ARR chat functionality validation not blocked

---

## 5. IMPLEMENTATION RECOMMENDATIONS

### 5.1 Immediate Fixes

1. **Reduce Docker Command Timeouts**: Change from 30s to 2s for availability checks
2. **Implement Fast-Fail Logic**: Detect Docker unavailability immediately
3. **Add Environment Mode Fallbacks**: Use staging/local when Docker unavailable
4. **Cache Docker Availability**: Avoid repeated expensive checks

### 5.2 Longer Term Improvements

1. **Docker-Optional Test Mode**: Allow WebSocket tests to run without Docker
2. **Staging Environment Integration**: First-class support for staging validation
3. **Test Environment Detection**: Automatic mode selection based on available services
4. **Performance Monitoring**: Track and alert on test execution times

---

## 6. RISK ASSESSMENT

### 6.1 Low Risk Changes
- Reducing Docker command timeouts
- Adding Docker availability caching  
- Implementing fast-fail logic

### 6.2 Medium Risk Changes
- Modifying WebSocket test infrastructure
- Adding alternative validation methods
- Environment mode fallback logic

### 6.3 Mitigation Strategies
- Gradual rollout of timeout changes
- Comprehensive test coverage for new failure modes
- Staging environment validation before production
- Rollback procedures for infrastructure changes

---

**Next Steps**: Implement failing tests first to validate issue reproduction, then implement fixes and validate with passing tests.