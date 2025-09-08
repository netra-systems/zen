# Test Failure Diagnosis Runbook

## 🚨 Critical Test Requirements

**CHEATING ON TESTS = ABOMINATION**
- Tests MUST use real services
- Tests MUST use real authentication  
- Tests MUST fail hard on errors
- E2E tests with 0.00s execution = AUTOMATIC FAILURE

## Quick Diagnosis Flow

```mermaid
graph TD
    A[Test Fails] --> B{What Type?}
    B -->|E2E| C[Check Real Services]
    B -->|Integration| D[Check Dependencies]
    B -->|Unit| E[Check Isolation]
    C --> F{Services Running?}
    F -->|No| G[Start Services]
    F -->|Yes| H[Check Auth]
    H --> I{Auth Working?}
    I -->|No| J[Fix Auth]
    I -->|Yes| K[Check WebSocket]
```

## Common Test Failure Patterns

### 1. E2E Test Shows 0.00s Execution
**Symptom**: Test completes instantly
**Root Cause**: Test is mocked/skipped
**Diagnosis**:
```bash
# Check for mocks
grep -r "Mock\|patch" tests/e2e/test_file.py
# Check for missing await
grep "async def test" tests/e2e/test_file.py | grep -v await
```
**Fix**:
- Remove all mocks from E2E tests
- Add proper await statements
- Use real services with --real-services

### 2. Authentication Failures
**Symptom**: 401/403 errors in tests
**Root Cause**: Missing or invalid auth
**Diagnosis**:
```python
# Check if test uses auth
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
auth_helper = E2EAuthHelper()
token = await auth_helper.get_test_token()
print(f"Token valid: {bool(token)}")
```
**Fix**:
- ALL E2E tests must use authentication
- Use E2EAuthHelper for SSOT auth patterns

### 3. WebSocket Connection Failures
**Symptom**: WebSocket tests timeout
**Root Cause**: WebSocket not initialized
**Diagnosis**:
```bash
# Check WebSocket bridge status
python -c "
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
import asyncio
async def check():
    bridge = AgentWebSocketBridge.get_instance()
    print(await bridge.get_status())
asyncio.run(check())
"
```
**Fix**:
```python
await bridge.ensure_integration(force_reinit=True)
```

### 4. Database Connection Errors
**Symptom**: psycopg2.OperationalError
**Root Cause**: Database not running
**Diagnosis**:
```bash
# Check if PostgreSQL is running
docker ps | grep postgres
# Check connection
psql postgresql://postgres:postgres@localhost:5434/test_db -c "SELECT 1"
```
**Fix**:
```bash
# Start database
python tests/unified_test_runner.py --real-services --keep-alive
```

### 5. Redis Connection Errors
**Symptom**: redis.ConnectionError
**Root Cause**: Redis not running
**Diagnosis**:
```bash
# Check if Redis is running
docker ps | grep redis
# Test connection
redis-cli -p 6381 ping
```
**Fix**:
```bash
# Start Redis
docker-compose -f docker-compose.alpine-test.yml up -d redis
```

### 6. Import Errors
**Symptom**: ModuleNotFoundError
**Root Cause**: Wrong import paths
**Diagnosis**:
```bash
# Check for relative imports
grep -r "from \.\." tests/ --include="*.py"
# Verify PYTHONPATH
echo $PYTHONPATH
```
**Fix**:
- Use absolute imports only
- Set PYTHONPATH to project root

### 7. Async Test Issues
**Symptom**: RuntimeWarning: coroutine never awaited
**Root Cause**: Missing async/await
**Diagnosis**:
```python
# Check test structure
# WRONG:
def test_something():
    result = async_function()  # Missing await!
    
# RIGHT:
async def test_something():
    result = await async_function()
```
**Fix**: Add async/await properly

## Test Layer Diagnosis

### E2E Test Failures
```bash
# 1. Verify all services running
docker ps
# Should see: postgres, redis, backend, auth, frontend

# 2. Check service health
curl http://localhost:8000/health
curl http://localhost:8081/health

# 3. Run with debug output
python tests/unified_test_runner.py --category e2e --verbose --real-services

# 4. Check for auth usage
grep "E2EAuthHelper\|get_test_token" tests/e2e/failing_test.py
```

### Integration Test Failures
```bash
# 1. Check dependencies
python -c "import netra_backend; import auth_service; print('Imports OK')"

# 2. Verify database migrations
alembic upgrade head

# 3. Run with isolated database
python tests/unified_test_runner.py --category integration --real-services
```

### Unit Test Failures
```bash
# 1. Check for unwanted dependencies
grep -r "docker\|redis\|postgres" tests/unit/

# 2. Verify mocks are appropriate
grep -r "Mock" tests/unit/failing_test.py

# 3. Run in isolation
python -m pytest tests/unit/failing_test.py -v
```

## Service-Specific Diagnosis

### Backend Service Tests
```python
# Check backend configuration
from netra_backend.app.core.managers.unified_configuration_manager import UnifiedConfigurationManager
config = UnifiedConfigurationManager()
print(f"Service ID: {config.service_id}")  # Must be "netra-backend"
print(f"Environment: {config.environment}")
```

### Auth Service Tests
```python
# Check auth configuration
from auth_service.auth_core.configuration import AuthConfig
config = AuthConfig()
print(f"OAuth configured: {bool(config.GOOGLE_CLIENT_ID)}")
print(f"JWT secret set: {bool(config.JWT_SECRET_KEY)}")
```

### WebSocket Tests
```python
# Check WebSocket events
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
bridge = AgentWebSocketBridge.get_instance()
await bridge.ensure_integration()
# Should trigger all 5 events during agent execution
```

## Test Runner Diagnosis

### When Tests Won't Start
```bash
# 1. Check Python version
python --version  # Should be 3.11+

# 2. Check test runner
python tests/unified_test_runner.py --help

# 3. Verify test discovery
python tests/unified_test_runner.py --list-tests
```

### When Docker Won't Start
```bash
# 1. Check Docker daemon
docker version

# 2. Clean up old containers
docker-compose -f docker-compose.alpine-test.yml down -v

# 3. Rebuild images
python tests/unified_test_runner.py --real-services --rebuild-all
```

### When Tests Hang
```bash
# 1. Check for deadlocks
# Add timeout to tests
pytest tests/e2e/ --timeout=30

# 2. Check for infinite loops
# Kill hanging process
pkill -f "python.*test"

# 3. Check resource limits
docker stats
```

## Mission Critical Test Validation

```bash
# The ONE test that must always pass
python tests/mission_critical/test_websocket_agent_events_suite.py

# Expected output:
# ✓ agent_started event detected
# ✓ agent_thinking event detected  
# ✓ tool_executing event detected
# ✓ tool_completed event detected
# ✓ agent_completed event detected
```

## Test Failure Recovery Steps

### Step 1: Clean Environment
```bash
# Stop everything
docker-compose -f docker-compose.alpine-test.yml down -v
pkill -f "python.*test"

# Clear test data
rm -rf test_artifacts/
rm -rf .pytest_cache/
```

### Step 2: Rebuild Services
```bash
# Rebuild Docker images
docker-compose -f docker-compose.alpine-test.yml build --no-cache

# Reinstall dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### Step 3: Verify Base Functionality
```bash
# Start services
python tests/unified_test_runner.py --real-services --keep-alive &

# Wait for services
sleep 10

# Test health endpoints
curl http://localhost:8000/health
curl http://localhost:8081/health
```

### Step 4: Run Progressive Tests
```bash
# 1. Smoke tests first
python tests/unified_test_runner.py --category smoke --real-services

# 2. Then unit tests
python tests/unified_test_runner.py --category unit

# 3. Then integration
python tests/unified_test_runner.py --category integration --real-services

# 4. Finally E2E
python tests/unified_test_runner.py --category e2e --real-services
```

## Debug Output Analysis

### Enable Maximum Verbosity
```bash
# Set debug logging
export LOG_LEVEL=DEBUG
export PYTEST_VERBOSE=true

# Run with all debug flags
python tests/unified_test_runner.py \
  --verbose \
  --show-output \
  --capture=no \
  --real-services \
  --category failing_category
```

### Analyze Log Patterns
```bash
# Check for errors
grep -i error test_output.log | head -20

# Check for warnings
grep -i warning test_output.log | head -20

# Check for WebSocket events
grep "WebSocket event" test_output.log

# Check for auth issues
grep -E "401|403|JWT|OAuth" test_output.log
```

## Test Categories Reference

- **smoke**: Basic functionality (< 1 min)
- **unit**: Isolated component tests (< 5 min)
- **integration**: Service integration tests (< 10 min)
- **api**: API endpoint tests (< 5 min)
- **e2e**: Full system tests (< 15 min)
- **performance**: Load and stress tests
- **security**: Security validation tests

## Emergency Contacts for Test Issues

- Test Framework: See `test_framework/README.md`
- Docker Issues: See `docker/README.md`
- CI/CD Pipeline: See `.github/workflows/`
- Architecture: See `docs/TEST_ARCHITECTURE_VISUAL_OVERVIEW.md`

## Test Failure Checklist

When a test fails:
- [ ] Identify test category (E2E/Integration/Unit)
- [ ] Check if real services are running
- [ ] Verify authentication is used
- [ ] Check for 0.00s execution time
- [ ] Look for mocks in E2E tests
- [ ] Verify WebSocket events if applicable
- [ ] Check database/Redis connectivity
- [ ] Review import statements
- [ ] Check async/await usage
- [ ] Run mission critical tests
- [ ] Document root cause

Diagnosed by: _______________
Date/Time: _______________
Test Name: _______________
Root Cause: _______________
Fix Applied: _______________