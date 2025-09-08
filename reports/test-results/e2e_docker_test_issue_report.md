# E2E Docker Test Issue Report

## Executive Summary

The e2e tests are failing to run with Docker due to multiple configuration and environment issues. The core problem is that the test framework's isolation system overrides environment variables, preventing tests from connecting to real Docker services.

## Root Causes Identified

### 1. **Test Isolation Override (PRIMARY ISSUE)**
- **Location**: `test_framework/conftest_real_services.py` and backend test configuration
- **Issue**: When tests are run, the isolation system sets `DATABASE_URL=sqlite+aiosqlite:/:memory:` even when real services are requested
- **Impact**: Tests cannot connect to PostgreSQL in Docker containers
- **Evidence**: All database tests show "Using PostgreSQL URL from testing configuration" but then fail to connect

### 2. **Docker Container Naming Mismatch**
- **Location**: `test_framework/unified_docker_manager.py`
- **Issue**: Containers are named `netra-apex-test-*-1` but UnifiedDockerManager has detection issues
- **Impact**: Health checks fail, containers not properly detected
- **Evidence**: "Container for service backend not found" errors despite containers running

### 3. **Service Discovery Logic Error**
- **Location**: `test_framework/unified_docker_manager.py:_detect_existing_dev_containers`
- **Issue**: When no containers match initial patterns, fallback logic incorrectly assumes Docker connectivity issues
- **Impact**: Manager falls back to wrong container names instead of using actual running containers

### 4. **Port Mapping Issues**
- **Current State**: Test containers expose ports 5434 (postgres), 6381 (redis), 8125 (clickhouse)
- **Issue**: Tests try to connect to these ports but are overridden by isolation

## Current Docker Container Status

```
Containers Running:
- netra-apex-test-frontend-1 (healthy)
- netra-apex-test-backend-1 (healthy) 
- netra-apex-test-auth-1 (healthy)
- netra-apex-test-postgres-1 (healthy)
- netra-apex-test-redis-1 (healthy)
- netra-apex-test-clickhouse-1 (healthy)
- netra-apex-test-monitor-1 (healthy)
- netra-apex-test-seeder-1 (healthy)
- netra-apex-test-rabbitmq-1 (healthy)
- netra-apex-test-mailhog-1 (healthy)
```

## Permanent Fixes Required

### Fix 1: Update Test Isolation Logic
**File**: `test_framework/conftest_real_services.py`

The isolation system needs to respect `USE_REAL_SERVICES` environment variable:
- When `USE_REAL_SERVICES=true`, do NOT override DATABASE_URL, REDIS_URL, etc.
- Allow real service URLs to pass through to the configuration

### Fix 2: Fix Container Detection in UnifiedDockerManager
**File**: `test_framework/unified_docker_manager.py`

Update `_detect_existing_dev_containers` method:
1. Remove incorrect fallback logic when containers list is empty
2. Properly handle `netra-apex-test-*` container naming pattern
3. Fix the `rstrip('-1')` logic that incorrectly strips container suffixes

### Fix 3: Update Test Runner Environment Setup
**File**: `tests/unified_test_runner.py`

The test runner should:
1. Set environment variables BEFORE importing test modules
2. Ensure `USE_REAL_SERVICES=true` is set early in the process
3. Disable test isolation when running with real services

### Fix 4: Create Service Configuration Override
**File**: `test_framework/service_config.py` (new)

Create a centralized service configuration that:
1. Detects when Docker containers are running
2. Automatically configures connection strings
3. Bypasses isolation when real services are available

## Workaround (Temporary)

Until permanent fixes are implemented, tests can be run with:

```bash
# Start Docker containers
docker-compose -f docker-compose.test.yml up -d

# Set environment to bypass isolation (doesn't fully work yet)
export USE_REAL_SERVICES=true
export SKIP_MOCKS=true
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5434/netra_test
export REDIS_URL=redis://localhost:6381/1

# Run tests directly (still fails due to isolation override)
pytest tests/agents/test_llm_agent_e2e_core.py
```

## Validation Steps

After fixes are implemented:

1. Start Docker containers with `docker-compose -f docker-compose.test.yml up -d`
2. Run `python tests/unified_test_runner.py --category e2e --real-services`
3. Verify tests connect to PostgreSQL on port 5434
4. Verify tests connect to Redis on port 6381
5. Verify WebSocket connections work on port 8001
6. All e2e tests should pass

## Impact

**Current State**: E2E tests cannot run with Docker services
**After Fix**: E2E tests will properly use Docker containers for realistic testing

## Priority: CRITICAL

This issue blocks all e2e testing with real services, which is essential for:
- Integration testing
- Performance testing
- Pre-deployment validation
- WebSocket functionality testing
- Multi-service orchestration testing

## Related Files

- `test_framework/conftest_real_services.py` - Real services configuration
- `test_framework/unified_docker_manager.py` - Docker container management
- `tests/unified_test_runner.py` - Main test runner
- `docker-compose.test.yml` - Docker service definitions
- `shared/isolated_environment.py` - Environment isolation system

## Next Steps

1. Implement Fix 1 (Test Isolation Logic) - Highest priority
2. Implement Fix 2 (Container Detection) - Required for health checks
3. Test fixes with a simple integration test
4. Update all e2e tests to use the fixed configuration
5. Document the proper usage in README

## Learnings

1. **Environment isolation is too aggressive** - It overrides even when explicitly told not to
2. **Container naming patterns matter** - The system must handle various Docker naming conventions
3. **Early environment setup is critical** - Environment must be configured before any imports
4. **Real services testing needs special handling** - Cannot treat real services same as mocks

## Conclusion

The core issue is that the test framework's isolation system is designed to prevent tests from accessing real services, but this prevents legitimate e2e testing with Docker. The system needs to be updated to allow real service connections when explicitly requested.

The fixes are straightforward but require careful coordination between multiple components of the test framework.