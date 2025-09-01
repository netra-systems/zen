# Test Infrastructure Docker & Environment Audit Report

## Executive Summary

**CRITICAL FINDING**: The test infrastructure is NOT properly integrated with the centralized Docker management system and is violating unified environment configuration requirements.

**Business Impact**: Test instability, environment drift, and increased debugging time affecting developer velocity.

## Major Compliance Issues Found

### 1. Direct Environment Variable Access (CRITICAL)

Multiple test files are using direct `os.getenv()` and `os.environ` access instead of the unified `IsolatedEnvironment`:

#### Violations Found:
- `tests/e2e/integration/test_agent_orchestration_real_llm.py:80` - Direct `os.getenv("TEST_LLM_TIMEOUT", "30")`  
- `tests/mission_critical/test_websocket_agent_events_suite.py:34` - Direct `os.getenv('WEBSOCKET_TEST_STAGING', 'false')`
- Many other tests using `os.environ` directly

**Required Fix**: All tests MUST use:
```python
from shared.isolated_environment import get_env
env = get_env()
timeout = env.get("TEST_LLM_TIMEOUT", "30")
```

### 2. Hardcoded Ports Instead of Dynamic Discovery (CRITICAL)

The test fixtures are hardcoding service ports instead of using CentralizedDockerManager's port discovery:

#### Current WRONG Pattern:
```python
# test_framework/conftest_real_services.py
env.set("TEST_POSTGRES_PORT", "5434", source="real_services_conftest")  # HARDCODED!
env.set("TEST_REDIS_PORT", "6381", source="real_services_conftest")     # HARDCODED!
```

#### Required CORRECT Pattern:
```python
from test_framework.centralized_docker_manager import CentralizedDockerManager

docker_manager = CentralizedDockerManager()
env_name, ports = docker_manager.acquire_environment()

# Use discovered ports
env.set("TEST_POSTGRES_PORT", str(ports["postgres"]), source="docker_discovery")
env.set("TEST_REDIS_PORT", str(ports["redis"]), source="docker_discovery")
```

### 3. Missing CentralizedDockerManager Integration (CRITICAL)

Tests are NOT using the centralized Docker manager's critical features:

#### Missing Integrations:
1. **No `acquire_environment()` calls** - Tests aren't acquiring managed environments
2. **No `_discover_ports()` usage** - Hardcoded ports will break with dynamic allocation
3. **No `release_environment()` cleanup** - Resource leaks in shared environments
4. **No restart rate limiting** - Risk of restart storms

### 4. CypressTestRunner Incomplete Integration

The `CypressTestRunner` initializes but doesn't USE the CentralizedDockerManager properly:

```python
# Current - CREATES but doesn't USE properly
self.docker_manager = CentralizedDockerManager(...)
```

Missing:
- No `acquire_environment()` call
- No port discovery integration
- Falls back to ServiceDependencyManager instead

## Detailed Test Analysis

### Top Priority Tests Requiring Fixes

#### 1. E2E Real LLM Agent Tests
**File**: `tests/e2e/integration/test_agent_orchestration_real_llm.py`
- Direct `os.getenv()` usage
- No Docker environment acquisition
- Hardcoded integration assumptions

#### 2. Mission Critical WebSocket Tests  
**File**: `tests/mission_critical/test_websocket_agent_events_suite.py`
- Direct environment variable access
- No unified configuration usage
- Missing Docker service coordination

#### 3. Real Services Conftest
**File**: `test_framework/conftest_real_services.py`
- Hardcoded all service ports
- Not using port discovery
- Missing environment lifecycle management

## Required Fixes

### Phase 1: Immediate Critical Fixes

1. **Update test_framework/conftest_real_services.py**:
```python
@pytest.fixture(scope="session", autouse=True)
async def real_services_session() -> AsyncIterator[RealServicesManager]:
    """Session-scoped real services with Docker integration."""
    from test_framework.centralized_docker_manager import CentralizedDockerManager
    from shared.isolated_environment import get_env
    
    env_manager = get_env()
    docker_manager = CentralizedDockerManager()
    
    # Acquire managed environment with dynamic ports
    env_name, ports = await docker_manager.acquire_environment()
    
    # Set discovered ports in isolated environment
    env_manager.set("TEST_POSTGRES_HOST", "localhost", source="docker_manager")
    env_manager.set("TEST_POSTGRES_PORT", str(ports["postgres"]), source="docker_manager")
    env_manager.set("TEST_REDIS_HOST", "localhost", source="docker_manager") 
    env_manager.set("TEST_REDIS_PORT", str(ports["redis"]), source="docker_manager")
    # ... other services
    
    try:
        # Wait for services to be healthy
        await docker_manager.wait_for_services()
        yield manager
    finally:
        # Release environment properly
        await docker_manager.release_environment(env_name)
```

2. **Fix all direct environment access**:
```python
# Replace ALL instances of:
os.getenv("KEY", "default")
os.environ["KEY"]

# With:
from shared.isolated_environment import get_env
env = get_env()
env.get("KEY", "default")
```

### Phase 2: Test-Specific Fixes

Each test file needs:
1. Import unified environment manager
2. Use Docker manager for service coordination
3. Properly acquire/release environments
4. Use discovered ports, not hardcoded values

### Phase 3: Validation

After fixes, validate:
1. No direct `os.environ` access (except in IsolatedEnvironment itself)
2. All tests use `acquire_environment()` for Docker services
3. Dynamic port discovery replaces hardcoded ports
4. Proper environment cleanup with `release_environment()`

## Compliance Checklist

Per SPEC/unified_environment_management.xml requirements:

- [ ] ❌ All services use IsolatedEnvironment for environment access
- [ ] ❌ No direct os.environ references outside unified config  
- [ ] ✅ All environment modifications include source tracking (when using env.set)
- [ ] ❌ Test environments use isolation mode
- [ ] ❌ Subprocess launches use get_subprocess_env()
- [ ] ✅ Thread-safe operations with RLock (IsolatedEnvironment has this)
- [ ] ❌ Legacy environment management code deleted

## Impact Analysis

### Current State Problems:
1. **Port Conflicts**: Hardcoded ports cause failures when services use different ports
2. **Environment Pollution**: Direct os.environ access causes test interference
3. **Resource Leaks**: No proper environment cleanup leads to resource exhaustion
4. **Restart Storms**: No rate limiting causes cascade failures

### After Fix Benefits:
1. **Dynamic Port Allocation**: Tests work regardless of actual port assignments
2. **Environment Isolation**: Tests can't interfere with each other
3. **Resource Management**: Proper acquisition/release prevents leaks
4. **Stability**: Rate limiting and coordination prevent cascade failures

## Recommended Action Plan

1. **Immediate** (TODAY):
   - Create task force to fix test_framework/conftest_real_services.py
   - Start migration of mission-critical tests

2. **Short Term** (This Week):
   - Fix all E2E real LLM tests
   - Update WebSocket test suites
   - Validate staging test compatibility

3. **Medium Term** (Next Sprint):
   - Migrate all remaining tests
   - Add pre-commit hooks to prevent regression
   - Update CI/CD validation

## Validation Script

Run this to find remaining violations:
```bash
# Find direct os.environ access
grep -r "os\.environ" tests/ --exclude-dir=__pycache__ | grep -v isolated_environment

# Find hardcoded ports
grep -r "543[0-9]\|638[0-9]\|812[0-9]" tests/ test_framework/

# Find missing Docker manager usage  
grep -L "CentralizedDockerManager\|acquire_environment" tests/e2e/*.py
```

## Conclusion

The test infrastructure requires immediate remediation to comply with the unified environment and centralized Docker management requirements. The fixes are straightforward but critical for system stability and developer productivity.

**Severity**: CRITICAL  
**Priority**: P0  
**Estimated Effort**: 2-3 days for critical paths, 1 week for full migration

---
Generated: 2025-01-09
Author: System Audit
Review Required: Yes