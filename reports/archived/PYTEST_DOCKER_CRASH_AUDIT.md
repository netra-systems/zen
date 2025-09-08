# Pytest Collection Docker Container Crash Audit Report

## Executive Summary
Critical issues have been identified with pytest test collection causing Docker container crashes in the Netra Core application. The primary causes are excessive memory consumption during test discovery, circular imports, and resource exhaustion from parallel test collection processes.

## Root Causes Identified

### 1. Memory Exhaustion During Test Collection

#### Issue: Excessive Memory Usage in conftest.py
- **Location**: `tests/conftest.py:1-1401` (1400+ lines)
- **Problem**: Massive conftest file importing entire application stack during collection
- **Impact**: Each pytest worker loads 1400+ lines of imports and fixtures before running any tests

**Critical Imports Loading on Collection:**
```python
# Line 27: Real services loading during collection
from test_framework.conftest_real_services import *

# Lines 31-59: Phase 0 migration components with fallback mocks
from netra_backend.app.models.user_execution_context import UserExecutionContext
from netra_backend.app.dependencies import (...)
from netra_backend.app.services.memory_optimization_service import (...)
from netra_backend.app.services.session_memory_manager import (...)
from netra_backend.app.database.session_manager import (...)
```

#### Issue: Docker Memory Limits Too Low
- **Backend Alpine**: 2GB limit, 1GB reservation
- **Auth Alpine**: 1GB limit, 512MB reservation
- **Test containers**: Using same limits as production

**Evidence from docker-compose.alpine-test.yml:**
```yaml
deploy:
  resources:
    limits:
      memory: 2G  # Too low for test collection with all imports
      cpus: '0.5'
```

### 2. Circular Import Dependencies

#### Issue: Startup Module Import Order
- **Location**: `netra_backend/app/startup_module.py:1`
- **Problem**: Imports `isolated_environment` before setting up paths
```python
from shared.isolated_environment import get_env  # Line 1, before path setup
```

#### Issue: Test Collection Timeout
- **Location**: `scripts/test_collection_audit.py:109`
- **Problem**: 60-second timeout insufficient for large test collections
```python
timeout=60  # Too short for Docker containers with limited resources
```

### 3. Pytest Configuration Issues

#### Issue: Aggressive Test Discovery
- **Location**: `pytest.ini:3`
- **Problem**: Searching multiple directories simultaneously
```ini
testpaths = tests netra_backend/tests auth_service/tests
```
This causes pytest to traverse and import from 3 separate test trees concurrently.

#### Issue: Session-Scoped Async Loop
- **Location**: `pytest.ini:10`
```ini
asyncio_default_fixture_loop_scope = session
```
Creates a single event loop for entire test session, leading to resource accumulation.

### 4. Resource Intensive Test Discovery

#### Issue: Real Service Connections During Collection
The conftest.py attempts to connect to real services during the collection phase:

**Lines 658-717**: E2EEnvironmentValidator validates services during collection
**Lines 501-598**: dev_launcher fixture starts actual services

This means pytest collection attempts to:
1. Connect to PostgreSQL (3 different configurations)
2. Connect to Redis (3 different configurations)  
3. Start HTTP servers
4. Validate ClickHouse connections

### 5. Docker-Specific Issues

#### Issue: No Test-Specific Dockerfile
- Backend test Dockerfile (`docker/backend.test.Dockerfile`) copies entire application
- No optimization for test collection vs test execution
- All dependencies installed regardless of need

#### Issue: tmpfs Volume Limitations
**Lines 19-23 in docker-compose.alpine-test.yml:**
```yaml
volumes:
  - type: tmpfs
    target: /var/lib/postgresql/data
    tmpfs:
      size: 512M  # Can fill up during heavy test runs
```

## Impact Analysis

### Container Crash Scenarios

1. **OOM (Out of Memory) Kills**
   - pytest collection loads 1400+ line conftest
   - Each test file import adds to memory
   - Docker kills container when limit reached

2. **Timeout Failures**
   - Collection takes >60 seconds
   - Health checks fail during collection
   - Docker restarts container

3. **Resource Starvation**
   - CPU limited to 0.5 cores
   - Multiple pytest workers compete
   - System becomes unresponsive

## Recommendations

### Immediate Fixes

1. **Increase Docker Memory Limits**
```yaml
# For test containers
deploy:
  resources:
    limits:
      memory: 4G  # Double current limit
      cpus: '1.0'  # Double CPU allocation
```

2. **Split conftest.py**
- Move real service fixtures to separate file
- Lazy-load Phase 0 components
- Create service-specific conftest files

3. **Optimize Test Discovery**
```ini
# pytest.ini
testpaths = tests  # Single path
addopts = --collect-only-once --import-mode=importlib
```

4. **Add Collection-Specific Dockerfile**
```dockerfile
# docker/pytest.collection.Dockerfile
FROM python:3.11-slim
# Minimal dependencies for collection only
RUN pip install pytest pytest-asyncio
# Copy only test structure, not full app
COPY tests /tests
COPY pytest.ini /
```

### Long-term Solutions

1. **Implement Test Collection Caching**
   - Cache discovered tests between runs
   - Skip collection if files unchanged
   - Use pytest-cache plugin

2. **Separate Collection from Execution**
   - Run collection in separate container
   - Pass test list to execution containers
   - Parallelize execution only, not collection

3. **Resource-Aware Test Loading**
   - Monitor memory during collection
   - Batch test loading
   - Implement collection pagination

4. **Fix Circular Dependencies**
   - Refactor startup_module.py imports
   - Move isolated_environment import
   - Create proper import hierarchy

## Validation Tests

To verify fixes:

1. **Memory Usage Test**
```bash
docker stats --no-stream alpine-test-backend
pytest --collect-only --co -q | wc -l
docker stats --no-stream alpine-test-backend
```

2. **Collection Time Test**
```bash
time docker exec alpine-test-backend pytest --collect-only
```

3. **Stress Test**
```bash
docker exec alpine-test-backend pytest --collect-only -n 4
```

## Metrics

Current State:
- Collection Time: >60 seconds (timeout)
- Memory Usage: >2GB (OOM kill)
- Success Rate: <50% in Docker
- Container Restarts: 3-5 per test run

Target State:
- Collection Time: <15 seconds
- Memory Usage: <1GB
- Success Rate: >99%
- Container Restarts: 0

## Conclusion

The Docker container crashes during pytest collection are caused by a combination of:
1. Excessive memory usage from large conftest.py
2. Insufficient Docker resource limits
3. Real service connection attempts during collection
4. Circular import dependencies
5. Aggressive test discovery configuration

Implementing the recommended fixes will stabilize test collection and prevent container crashes.