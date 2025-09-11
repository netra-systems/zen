# Test Plan: WebSocket Docker Timeout Fix

## Impact
Mission critical WebSocket test suite hangs 120+ seconds when Docker unavailable, blocking validation of chat functionality ($500K+ ARR). Need fast-fail mechanism and alternative validation paths.

## Root Cause
- Docker availability checks use 30s timeouts via `DockerRateLimiter.execute_docker_command()`
- Multiple Docker commands create cumulative 120+ second hangs 
- WebSocket tests require Docker but have no graceful degradation

## Test Strategy

### Phase 1: Reproduce Issue (Failing Tests)
**Purpose**: Prove current hanging behavior exists

**Key Tests**:
- `test_docker_availability_timeout_reproduction()` - Should FAIL showing 30s+ timeout
- `test_multiple_docker_commands_cumulative_timeout()` - Should FAIL showing 120s+ cumulative hang
- `test_websocket_test_suite_hanging_behavior()` - Should FAIL showing test suite hangs

### Phase 2: Validate Fix (Passing Tests)  
**Purpose**: Confirm fast-fail and graceful degradation work

**Key Tests**:
- `test_docker_availability_fast_fail_when_unavailable()` - Should complete < 1s
- `test_require_docker_services_fast_fail()` - Should fail immediately, not hang
- `test_websocket_staging_validation()` - Alternative validation when Docker unavailable

## Test Files Created

1. **`tests/unit/test_docker_availability_timeout_issue411.py`**
   - Reproduces 30s timeout behavior (SHOULD FAIL initially)
   - Validates fast-fail after fix (SHOULD PASS after implementation)

2. **`tests/unit/test_rate_limiter_cumulative_timeout_issue411.py`**  
   - Demonstrates cumulative timeout problem (SHOULD FAIL initially)
   - Validates timeout handling improvements (SHOULD PASS after fix)

3. **`tests/integration/test_websocket_docker_graceful_degradation_issue411.py`**
   - Tests WebSocket infrastructure graceful failure modes
   - Validates alternative test paths when Docker unavailable

4. **`tests/e2e/test_websocket_staging_validation_issue411.py`**
   - Alternative WebSocket validation using staging environment
   - Enables WebSocket event testing without local Docker

## Success Criteria

| Metric | Before Fix | After Fix | Target |
|--------|------------|-----------|---------|
| Docker availability check | 30+ seconds | < 2 seconds | 93%+ faster |
| WebSocket test failure | 120+ seconds | < 5 seconds | 95%+ faster |
| Test feedback loop | 2+ minutes | < 10 seconds | 91%+ faster |

## Implementation Plan

### Immediate Fixes
1. **Reduce Docker timeouts**: 30s → 2s for availability checks in `DockerRateLimiter`
2. **Fast-fail logic**: Detect Docker unavailable immediately in `UnifiedDockerManager.is_docker_available()`  
3. **Test suite graceful failure**: Update `require_docker_services()` to fail fast
4. **Docker availability caching**: Cache results to avoid repeated expensive checks

### Alternative Validation
1. **Staging WebSocket tests**: Enable WebSocket event validation using staging environment
2. **Service mode fallback**: Automatic fallback to LOCAL mode when Docker unavailable
3. **Environment detection**: Smart test mode selection based on available services

## Execution Commands

```bash
# Reproduce issue (should FAIL initially)
python -m pytest tests/unit/test_docker_availability_timeout_issue411.py::test_docker_availability_check_timeout_reproduction -v

# Validate fix (should PASS after implementation)  
python -m pytest tests/unit/test_fast_docker_availability_issue411.py::test_docker_availability_fast_fail_when_unavailable -v

# Test WebSocket graceful degradation
python -m pytest tests/integration/test_websocket_docker_graceful_degradation_issue411.py -v

# Validate no more hanging (should complete quickly)
timeout 30 python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Business Value
- **Developer Productivity**: No more 2+ minute waits when Docker unavailable
- **CI/CD Speed**: Faster feedback in Docker-less environments  
- **WebSocket Validation**: Critical chat functionality ($500K+ ARR) validation unblocked
- **Platform Reliability**: Alternative test paths ensure continuous validation

Full test plan: [`TEST_PLAN_ISSUE_411_WEBSOCKET_DOCKER_TIMEOUT.md`](./TEST_PLAN_ISSUE_411_WEBSOCKET_DOCKER_TIMEOUT.md)