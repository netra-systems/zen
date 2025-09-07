# Common Mistakes Runbook

## 🚨 Top 10 Most Common Mistakes That Break Everything

### 1. SERVICE_ID with Timestamps
**Symptom**: Authentication fails every minute
**Root Cause**: SERVICE_ID changes with timestamp suffix
**How to Check**:
```bash
grep -r "SERVICE_ID.*datetime" .
grep -r "service_id.*timestamp" .
```
**Fix**: SERVICE_ID must ALWAYS be "netra-backend" (stable value)
**Reference**: `SPEC/learnings/service_id_stability_fix_20250907.xml`

### 2. Missing WebSocket Events
**Symptom**: Chat appears frozen, no agent progress visible
**Root Cause**: One or more of 5 critical events not sent
**How to Check**:
```bash
python tests/mission_critical/test_websocket_agent_events_suite.py
```
**Required Events**:
1. agent_started
2. agent_thinking  
3. tool_executing
4. tool_completed
5. agent_completed
**Fix**: Ensure AgentWebSocketBridge properly initialized

### 3. Environment Config Leakage
**Symptom**: Staging uses production resources or vice versa
**Root Cause**: Configs not properly isolated per environment
**How to Check**:
```python
# In any service
from shared.isolated_environment import IsolatedEnvironment
env = IsolatedEnvironment()
print(f"Environment: {env.get('ENVIRONMENT')}")
print(f"OAuth: {env.get('GOOGLE_CLIENT_ID')}")
```
**Fix**: Each environment needs INDEPENDENT config files

### 4. Direct os.environ Access
**Symptom**: Config changes don't take effect, wrong values used
**Root Cause**: Bypassing IsolatedEnvironment
**How to Check**:
```bash
grep -r "os\.environ\[" . --include="*.py" | grep -v isolated_environment
```
**Fix**: ALL env access through IsolatedEnvironment

### 5. Shared State Between Users
**Symptom**: User A sees User B's data/results
**Root Cause**: Singleton classes with user-specific state
**How to Check**:
```python
# Look for patterns like:
class SomeManager:
    _instance = None
    user_data = {}  # WRONG! Shared across all users
```
**Fix**: Use factory pattern for user-specific instances

### 6. Non-Idempotent Initialization
**Symptom**: Race conditions, duplicate registrations, startup failures
**Root Cause**: Init methods not safe to call multiple times
**How to Check**:
```python
# Try calling init twice
bridge = AgentWebSocketBridge.get_instance()
await bridge.ensure_integration()
await bridge.ensure_integration()  # Should not fail
```
**Fix**: Add state checking, make initialization idempotent

### 7. Silent Error Suppression
**Symptom**: System appears to work but actually failing
**Root Cause**: try/except blocks swallowing errors
**How to Check**:
```bash
grep -r "except.*pass" . --include="*.py"
grep -r "except Exception:" . --include="*.py" | grep -v "raise\|log"
```
**Fix**: Always log errors, never silent failures

### 8. Mocked Services in E2E Tests
**Symptom**: Tests pass but production fails
**Root Cause**: E2E tests using mocks instead of real services
**How to Check**:
```bash
grep -r "Mock\|patch" tests/e2e/ --include="*.py"
```
**Fix**: E2E must use real services with --real-services flag

### 9. Missing OAuth Credentials
**Symptom**: 503 errors, auth service fails
**Root Cause**: OAuth credentials deleted or missing
**How to Check**:
```bash
# Check each environment file
cat auth_service/.env.staging | grep GOOGLE_CLIENT
cat auth_service/.env.production | grep GOOGLE_CLIENT
```
**Fix**: Each environment needs complete OAuth credentials

### 10. Cross-Service Direct Imports
**Symptom**: Circular dependencies, import errors
**Root Cause**: Services importing from each other directly
**How to Check**:
```bash
# From netra_backend, should not import from auth_service
grep -r "from auth_service" netra_backend/ --include="*.py"
# From auth_service, should not import from netra_backend  
grep -r "from netra_backend" auth_service/ --include="*.py"
```
**Fix**: Only import from /shared for cross-service code

## Race Condition Patterns to Avoid

### Pattern 1: Concurrent WebSocket Initialization
```python
# WRONG - Race condition
async def handle_request():
    bridge = AgentWebSocketBridge.get_instance()
    await bridge.ensure_integration()  # Multiple requests race here
    
# RIGHT - Idempotent
async def handle_request():
    bridge = AgentWebSocketBridge.get_instance()
    await bridge.ensure_integration()  # Safe to call concurrently
```

### Pattern 2: Shared Mutable State
```python
# WRONG - Shared state
class AgentManager:
    results = {}  # Shared across all users!
    
# RIGHT - Request-scoped
class AgentManager:
    def __init__(self, user_id):
        self.results = {}  # Per-user instance
```

### Pattern 3: Non-Atomic Operations
```python
# WRONG - Not atomic
if not self.initialized:
    # Another thread can enter here
    self.initialize()
    self.initialized = True
    
# RIGHT - Atomic with lock
async with self._init_lock:
    if not self.initialized:
        await self.initialize()
        self.initialized = True
```

## Emergency Recovery Procedures

### When WebSocket Events Stop Working
1. Check AgentWebSocketBridge status:
```python
bridge = AgentWebSocketBridge.get_instance()
status = await bridge.get_status()
print(status)
```
2. Force reinitialize if needed:
```python
await bridge.ensure_integration(force_reinit=True)
```
3. Verify events in logs:
```bash
grep "WebSocket event" logs/backend.log | tail -20
```

### When Authentication Breaks
1. Check SERVICE_ID stability:
```bash
grep SERVICE_ID netra_backend/app/core/configuration/services.py
```
2. Verify JWT secret:
```python
from shared.jwt_secret_manager import JWTSecretManager
manager = JWTSecretManager()
print(manager.get_secret())
```
3. Check OAuth credentials exist:
```bash
python scripts/check_auth_ssot_compliance.py
```

### When Tests Show 0.00s Execution
1. Tests are being skipped/mocked
2. Check for missing await:
```python
# WRONG
def test_something():
    result = async_function()  # Missing await!
    
# RIGHT  
async def test_something():
    result = await async_function()
```
3. Verify real services running:
```bash
docker ps | grep -E "postgres|redis|backend|auth"
```

## Verification Commands

### Quick Health Check
```bash
# Check all critical services
python scripts/check_auth_ssot_compliance.py
python tests/mission_critical/test_websocket_agent_events_suite.py
python tests/unified_test_runner.py --category smoke --real-services
```

### Deep Verification
```bash
# Full system check
python tests/unified_test_runner.py --categories integration e2e --real-services
python scripts/check_architecture_compliance.py
```

### Configuration Validation
```bash
# Check for config issues
grep -r "os\.environ" . --include="*.py" | grep -v isolated_environment
grep -r "SERVICE_ID" . --include="*.py" | grep -v "netra-backend"
```

## Prevention Strategies

1. **Always run mission critical tests before commit**
2. **Use TodoWrite for complex changes**
3. **Check MISSION_CRITICAL_NAMED_VALUES_INDEX.xml**
4. **Verify with multiple concurrent users**
5. **Test in staging before production**
6. **Look for "error behind the error" (up to 10 levels deep)**
7. **Never add fallbacks without explicit design**
8. **Maintain SSOT - one implementation per concept**
9. **Make all errors loud and visible**
10. **Complete the Definition of Done checklist**