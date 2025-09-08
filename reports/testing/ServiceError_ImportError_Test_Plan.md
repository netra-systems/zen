# ServiceError ImportError Test Creation Plan

**Business Value Justification (BVJ):**
- **Segment:** Platform/Internal - Development Velocity, Risk Reduction  
- **Business Goal:** Ensure system reliability and prevent Docker container startup failures
- **Value Impact:** Prevents ImportError failures that block critical services and chat functionality
- **Strategic Impact:** Protects business-critical WebSocket notifications and agent executions from import failures

## Problem Statement

**ImportError Issue:** `cannot import name 'ServiceError' from 'netra_backend.app.core.exceptions'`

**Context Analysis:**
- ServiceError is properly defined in `exceptions_service.py` line 7-16
- Import chain: `exceptions/__init__.py` → `exceptions_service.py` → `exceptions_agent.py`  
- Error occurs in Docker container environment (`/app/netra_backend/app/core/exceptions/__init__.py`)
- Local imports work fine, suggesting timing/race condition during container startup
- Complex circular dependency potential: `exceptions_service.py` imports `AgentExecutionError` from `exceptions_agent.py`

## Test Categories and Scenarios

### 1. Unit Tests - Import Reliability

**File Location:** `netra_backend/tests/unit/test_exception_import_reliability.py`

**Test Scenarios:**

#### 1.1 Direct Import Tests
```python
def test_service_error_import_direct():
    """Test ServiceError can be imported directly from exceptions_service."""
    # Business Value: Ensures base exception class is always available
    from netra_backend.app.core.exceptions_service import ServiceError
    assert ServiceError is not None
    assert issubclass(ServiceError, Exception)

def test_service_error_import_from_init():
    """Test ServiceError can be imported from exceptions __init__.""" 
    # Business Value: Validates public API import path works
    from netra_backend.app.core.exceptions import ServiceError
    assert ServiceError is not None

def test_service_error_instantiation():
    """Test ServiceError can be instantiated with default parameters."""
    # Business Value: Ensures exception can be raised when needed
    from netra_backend.app.core.exceptions import ServiceError
    error = ServiceError()
    assert str(error) == "Service error occurred"
```

#### 1.2 Import Order Dependency Tests
```python
def test_import_order_exceptions_service_first():
    """Test importing exceptions_service before __init__ works."""
    # This test MUST FAIL initially to reproduce the timing issue
    import sys
    # Clear modules to simulate fresh container startup
    modules_to_clear = [mod for mod in sys.modules if 'netra_backend.app.core.exceptions' in mod]
    for mod in modules_to_clear:
        del sys.modules[mod]
    
    # Import service first, then __init__ - this may reveal timing issues
    from netra_backend.app.core.exceptions_service import ServiceError
    from netra_backend.app.core.exceptions import ServiceError as InitServiceError
    assert ServiceError is InitServiceError

def test_import_order_init_first():
    """Test importing __init__ before exceptions_service works."""
    # Business Value: Tests normal import pattern
    import sys
    modules_to_clear = [mod for mod in sys.modules if 'netra_backend.app.core.exceptions' in mod]
    for mod in modules_to_clear:
        del sys.modules[mod]
    
    from netra_backend.app.core.exceptions import ServiceError
    from netra_backend.app.core.exceptions_service import ServiceError as DirectServiceError
    assert ServiceError is DirectServiceError
```

#### 1.3 Circular Import Detection Tests
```python
def test_circular_import_detection():
    """Test for potential circular imports in exception hierarchy."""
    # Business Value: Prevents import deadlocks that cause ServiceError ImportError
    import importlib
    import sys
    
    # Clear all exception modules
    exception_modules = [mod for mod in sys.modules if 'exceptions' in mod and 'netra_backend' in mod]
    for mod in exception_modules:
        del sys.modules[mod]
    
    # Track import order to detect cycles
    import_order = []
    original_import = __builtins__['__import__']
    
    def tracking_import(name, *args, **kwargs):
        if 'exceptions' in name and 'netra_backend' in name:
            import_order.append(name)
        return original_import(name, *args, **kwargs)
    
    __builtins__['__import__'] = tracking_import
    
    try:
        from netra_backend.app.core.exceptions import ServiceError
        # Check for circular patterns
        assert len(set(import_order)) == len(import_order), f"Circular import detected: {import_order}"
    finally:
        __builtins__['__import__'] = original_import
```

### 2. Integration Tests - Docker Environment Import Issues

**File Location:** `netra_backend/tests/integration/test_exception_docker_import.py`

**Test Scenarios:**

#### 2.1 Container Startup Import Tests  
```python
@pytest.mark.integration
@pytest.mark.real_services
async def test_service_error_import_in_fresh_container(real_services_fixture):
    """Test ServiceError import works in fresh Docker container environment."""
    # Business Value: Reproduces the exact production failure scenario
    docker_manager = real_services_fixture["docker_manager"]
    
    # Stop and restart backend container to simulate fresh startup
    await docker_manager.stop_service("backend")
    await asyncio.sleep(2)  # Allow container to fully stop
    
    # Start backend and immediately test imports
    result = await docker_manager.start_service("backend")
    assert result.success
    
    # Execute import test inside container
    import_test_code = """
import sys
sys.path.insert(0, '/app')
from netra_backend.app.core.exceptions import ServiceError
print(f"SUCCESS: ServiceError imported: {ServiceError}")
    """
    
    # This test SHOULD FAIL initially to reproduce the bug
    exec_result = await docker_manager.execute_in_container("backend", ["python", "-c", import_test_code])
    assert exec_result.return_code == 0, f"Import failed: {exec_result.stderr}"

@pytest.mark.integration 
@pytest.mark.real_services
async def test_concurrent_exception_imports(real_services_fixture):
    """Test concurrent imports of ServiceError from multiple threads."""
    # Business Value: Tests race conditions during container initialization
    docker_manager = real_services_fixture["docker_manager"]
    
    import_results = []
    
    async def concurrent_import_test(worker_id):
        test_code = f"""
import sys
sys.path.insert(0, '/app')
# Worker {worker_id} importing ServiceError
from netra_backend.app.core.exceptions import ServiceError
print(f"Worker {worker_id}: SUCCESS")
        """
        result = await docker_manager.execute_in_container("backend", ["python", "-c", test_code])
        import_results.append((worker_id, result.return_code, result.stderr))
    
    # Run 5 concurrent import attempts
    tasks = [concurrent_import_test(i) for i in range(5)]
    await asyncio.gather(*tasks)
    
    # All imports should succeed
    failures = [(wid, code, err) for wid, code, err in import_results if code != 0]
    assert len(failures) == 0, f"Concurrent import failures: {failures}"
```

#### 2.2 Module Loading Timing Tests
```python
@pytest.mark.integration
@pytest.mark.real_services  
async def test_module_loading_timing_under_load(real_services_fixture):
    """Test exception module loading under simulated system load."""
    # Business Value: Tests import reliability under realistic container stress
    docker_manager = real_services_fixture["docker_manager"]
    
    # Create CPU load simulation
    load_test_code = """
import threading
import time
import sys
sys.path.insert(0, '/app')

def cpu_load():
    for _ in range(1000000):
        pass

# Start background load
threads = [threading.Thread(target=cpu_load) for _ in range(3)]
for t in threads:
    t.start()

# Now try to import under load
try:
    from netra_backend.app.core.exceptions import ServiceError
    print("SUCCESS: Import under load worked")
except ImportError as e:
    print(f"FAILED: Import under load failed: {e}")
    raise

for t in threads:
    t.join()
    """
    
    result = await docker_manager.execute_in_container("backend", ["python", "-c", load_test_code])
    assert result.return_code == 0, f"Import under load failed: {result.stderr}"
```

### 3. E2E Tests - Exception Handling in Real Workflows

**File Location:** `netra_backend/tests/e2e/test_exception_handling_workflows.py`

**Test Scenarios:**

#### 3.1 Agent Execution Exception Path Tests
```python
@pytest.mark.e2e
@pytest.mark.real_llm
@pytest.mark.mission_critical
async def test_service_error_in_agent_execution(real_services, real_llm):
    """Test ServiceError can be raised and handled in real agent execution."""
    # Business Value: Ensures exceptions work in business-critical agent flows
    
    # Create user and WebSocket connection
    user = await create_test_user(email="exception@test.com")
    
    async with WebSocketTestClient(token=user.token) as client:
        # Send request that will trigger service error handling
        await client.send_json({
            "type": "agent_request", 
            "agent": "triage_agent",
            "message": "trigger_service_error_test"  # Special test message
        })
        
        events = []
        async for event in client.receive_events(timeout=30):
            events.append(event)
            if event["type"] == "agent_completed" or event["type"] == "error":
                break
        
        # Verify ServiceError can be imported and used in error responses
        error_events = [e for e in events if e["type"] == "error"]
        if error_events:
            error_event = error_events[0]
            # Ensure error was properly handled using ServiceError class
            assert "ServiceError" in str(error_event.get("data", {}))

@pytest.mark.e2e
@pytest.mark.real_services
async def test_websocket_exception_propagation(real_services):
    """Test exception propagation through WebSocket layer uses ServiceError."""
    # Business Value: Validates error handling in chat infrastructure
    
    user = await create_test_user(email="websocket@test.com")
    
    async with WebSocketTestClient(token=user.token) as client:
        # Send malformed request to trigger exception handling
        await client.send_json({
            "type": "invalid_request_type",
            "malformed": "data"
        })
        
        # Should receive error response using proper exception classes
        response = await client.receive_json(timeout=10)
        assert response["type"] == "error"
        
        # Error should be handled by ServiceError-based exception system  
        error_data = response.get("data", {})
        assert "message" in error_data
        assert error_data["message"] is not None
```

### 4. Container Environment Specific Tests

**File Location:** `netra_backend/tests/integration/test_container_import_environment.py`

**Test Scenarios:**

#### 4.1 Python Path and Module Discovery Tests
```python
@pytest.mark.integration
@pytest.mark.real_services
async def test_python_path_consistency_in_container(real_services_fixture):
    """Test Python path and module discovery in container vs local."""
    # Business Value: Identifies path issues causing import failures
    
    docker_manager = real_services_fixture["docker_manager"]
    
    path_test_code = """
import sys
import os
print("PYTHON PATH:")
for p in sys.path:
    print(f"  {p}")

print("\\nWORKING DIRECTORY:", os.getcwd())
print("\\nFILES IN /app:")
for root, dirs, files in os.walk('/app'):
    for file in files:
        if 'exceptions' in file:
            print(f"  {os.path.join(root, file)}")

print("\\nTESTING MODULE DISCOVERY:")
try:
    import netra_backend
    print(f"netra_backend module found at: {netra_backend.__file__}")
except ImportError as e:
    print(f"netra_backend import failed: {e}")

try:
    import netra_backend.app.core.exceptions_service
    print("exceptions_service module found")
except ImportError as e:
    print(f"exceptions_service import failed: {e}")
    """
    
    result = await docker_manager.execute_in_container("backend", ["python", "-c", path_test_code])
    # This diagnostic test should always pass
    assert result.return_code == 0, f"Path diagnosis failed: {result.stderr}"

@pytest.mark.integration
@pytest.mark.real_services
async def test_file_system_timing_in_container(real_services_fixture):
    """Test file system timing issues in container startup."""
    # Business Value: Identifies filesystem race conditions during container init
    
    docker_manager = real_services_fixture["docker_manager"]
    
    timing_test_code = """
import time
import os
import sys
sys.path.insert(0, '/app')

print("Testing file availability during startup:")
for i in range(10):
    files_exist = []
    files_exist.append(os.path.exists('/app/netra_backend/app/core/exceptions/__init__.py'))
    files_exist.append(os.path.exists('/app/netra_backend/app/core/exceptions_service.py'))
    files_exist.append(os.path.exists('/app/netra_backend/app/core/exceptions_agent.py'))
    
    print(f"Attempt {i+1}: __init__.py={files_exist[0]}, service={files_exist[1]}, agent={files_exist[2]}")
    
    if all(files_exist):
        try:
            from netra_backend.app.core.exceptions import ServiceError
            print(f"SUCCESS on attempt {i+1}")
            break
        except ImportError as e:
            print(f"IMPORT FAILED on attempt {i+1}: {e}")
    
    time.sleep(0.1)
else:
    print("FAILED: Could not import ServiceError after 10 attempts")
    """
    
    result = await docker_manager.execute_in_container("backend", ["python", "-c", timing_test_code])
    # This test may fail initially - that's expected to reproduce timing issues
    if result.return_code != 0:
        print(f"Timing test revealed issues: {result.stdout}")
        print(f"Errors: {result.stderr}")
```

### 5. Load and Stress Tests for Import System

**File Location:** `netra_backend/tests/integration/test_exception_import_stress.py`

**Test Scenarios:**

#### 5.1 High-Frequency Import Tests
```python
@pytest.mark.integration
@pytest.mark.real_services
async def test_high_frequency_exception_imports(real_services_fixture):
    """Test importing ServiceError under high-frequency access patterns."""
    # Business Value: Simulates production load patterns that may trigger import issues
    
    docker_manager = real_services_fixture["docker_manager"]
    
    stress_test_code = """
import sys
import threading
import time
sys.path.insert(0, '/app')

success_count = 0
failure_count = 0
failures = []

def import_test_worker(worker_id, iterations):
    global success_count, failure_count, failures
    
    for i in range(iterations):
        try:
            # Clear module cache to force re-import
            if 'netra_backend.app.core.exceptions' in sys.modules:
                del sys.modules['netra_backend.app.core.exceptions']
            
            from netra_backend.app.core.exceptions import ServiceError
            success_count += 1
        except ImportError as e:
            failure_count += 1
            failures.append(f"Worker {worker_id} iteration {i}: {e}")
        
        time.sleep(0.001)  # 1ms between attempts

# Run 10 threads, 50 imports each
threads = []
for worker_id in range(10):
    t = threading.Thread(target=import_test_worker, args=(worker_id, 50))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"SUCCESS: {success_count}, FAILURES: {failure_count}")
if failures:
    print("FAILURE DETAILS:")
    for f in failures[:10]:  # Show first 10 failures
        print(f"  {f}")

# Test should have very low failure rate (< 1%)
assert failure_count < success_count * 0.01, f"Too many import failures: {failure_count}"
    """
    
    result = await docker_manager.execute_in_container("backend", ["python", "-c", stress_test_code])
    assert result.return_code == 0, f"Stress test failed: {result.stderr}"
```

## Test Execution Methodology

### Phase 1: Reproduce the Bug (Expected Failures)
1. **Unit Tests** - Run import order and circular dependency tests
2. **Integration Tests** - Run fresh container startup tests
3. **Expected Result**: Some tests should FAIL initially, confirming the import issue

### Phase 2: Environment Analysis  
1. **Container Environment Tests** - Diagnose Python path and timing issues
2. **Load Tests** - Identify conditions that trigger the import failure
3. **Expected Result**: Collect diagnostic data about import failure conditions

### Phase 3: Fix Validation
1. After implementing fix, re-run all tests
2. **Success Criteria**: All tests pass consistently across multiple runs
3. **Load Tests**: No import failures under stress conditions

## Test Environment Requirements

### Docker Environment Configuration
- **Test Environment**: PostgreSQL (5434), Redis (6381), Backend (8000), Auth (8081)
- **Alpine Container Support**: Use `--real-services` with Alpine containers for faster startup
- **Container Restart Testing**: Tests will stop/start containers to simulate fresh startup conditions

### Test Execution Commands

```bash
# Unit tests for import reliability
python tests/unified_test_runner.py --test-file netra_backend/tests/unit/test_exception_import_reliability.py

# Integration tests with Docker  
python tests/unified_test_runner.py --test-file netra_backend/tests/integration/test_exception_docker_import.py --real-services

# Container environment tests
python tests/unified_test_runner.py --test-file netra_backend/tests/integration/test_container_import_environment.py --real-services

# E2E exception handling tests
python tests/unified_test_runner.py --test-file netra_backend/tests/e2e/test_exception_handling_workflows.py --category e2e --real-llm

# Full exception import test suite
python tests/unified_test_runner.py --categories unit integration e2e --pattern "*exception*import*" --real-services
```

## Success Criteria

### Immediate Success Criteria (Must Pass After Fix)
1. **ServiceError Direct Import**: Can import ServiceError from both `exceptions_service` and `exceptions/__init__.py`
2. **Container Startup Reliability**: ServiceError imports work in fresh Docker containers 100% of the time
3. **Concurrent Access**: Multiple threads can import ServiceError simultaneously without failures
4. **Load Testing**: < 1% import failure rate under high-frequency access patterns

### Business Value Success Criteria  
1. **Chat Functionality Protected**: Agent execution can properly handle ServiceError exceptions
2. **WebSocket Reliability**: Exception propagation through WebSocket layer works correctly
3. **Production Stability**: No import-related failures in staging/production deployment tests

### Performance Success Criteria
1. **Import Speed**: ServiceError import completes in < 100ms in container environment
2. **Memory Usage**: Import process doesn't cause memory leaks or excessive allocation
3. **Container Startup Time**: Import issues don't delay container readiness checks

## Risk Mitigation

### High-Risk Scenarios
1. **Circular Import Deadlock**: Tests detect and fail fast on circular dependencies
2. **Module Cache Corruption**: Tests clear and reload modules to simulate fresh state
3. **Race Conditions**: Concurrent tests identify timing-sensitive import issues

### Fallback Strategies
1. **Import Path Analysis**: Diagnostic tests provide detailed module discovery information
2. **Timing Analysis**: Tests measure import performance to identify bottlenecks
3. **Environment Comparison**: Tests compare container vs local import behavior

## Implementation Notes

### Test Framework Integration
- **Follows TEST_CREATION_GUIDE.md**: Uses SSOT patterns and real services approach
- **Base Classes**: Inherits from `BaseIntegrationTest` and `BaseE2ETest` for consistency  
- **Docker Management**: Uses `UnifiedDockerManager` for container operations
- **WebSocket Testing**: Uses `WebSocketTestClient` for E2E agent interaction tests

### SSOT Compliance
- **Import Management**: Tests use absolute imports following `import_management_architecture.xml`
- **Configuration**: Uses `IsolatedEnvironment` instead of direct `os.environ` access
- **Error Handling**: Tests validate proper use of exception hierarchy and error codes

### Monitoring and Reporting
- **Test Metrics**: Track import success rates, timing, and failure patterns
- **CI/CD Integration**: Tests run on every commit affecting exception modules
- **Production Monitoring**: Import health checks in staging/production environments

---

*This test plan ensures comprehensive coverage of the ServiceError ImportError issue while following Netra's SSOT testing principles and business value focus.*