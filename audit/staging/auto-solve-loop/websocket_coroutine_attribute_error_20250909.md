# WebSocket Coroutine Attribute Error - Critical Regression Analysis
## Issue: WebSocket endpoint failure blocking chat functionality

**Date:** 2025-09-09
**Severity:** ERROR  
**Location:** `netra_backend.app.routes.websocket:557` in `websocket_endpoint`
**Error Message:** `WebSocket error: 'coroutine' object has no attribute 'get'`

## Evidence from GCP Staging Logs

### Error Instances
1. **2025-09-07T15:42:02.024757Z** - insertId: 68bda7ca000060b5c52605c7
2. **2025-09-07T15:42:01.011130Z** - insertId: 68bda7c900002b7a2696a3e8  
3. **2025-09-07T15:42:00.635880Z** - insertId: 68bda7c80009b3e8740b423f

### Associated HTTP Failures  
- **HTTP 500 responses** on `/ws` endpoint
- **User-Agent:** "Netra-E2E-Tests/1.0" (indicates E2E test failures)
- **Response size:** 99 bytes (likely error response)

### Business Impact
- **Critical Chat Functionality Disruption:** WebSocket connections failing prevents real-time AI interactions
- **User Experience Degradation:** No live agent communication possible
- **Test Suite Failures:** E2E tests cannot validate chat workflows

## Root Cause Analysis Status
- [ ] Five Whys analysis completed
- [ ] Code inspection at line 557 completed  
- [ ] Coroutine handling pattern identified
- [ ] Fix implemented and tested
- [ ] System stability validated

## Five Whys Analysis Results

### Why 1: Why is the coroutine object missing the 'get' attribute?
**Direct cause**: The code is calling `.get()` on a coroutine object instead of an `IsolatedEnvironment` instance. Coroutines don't have a `.get()` method - they need to be awaited first.

### Why 2: Why is the code trying to call .get() on a coroutine?
**Immediate contributing factor**: The `get_env()` function is returning a coroutine instead of an `IsolatedEnvironment` instance. The WebSocket code expects synchronous object with `.get()` method.

### Why 3: Why is a coroutine being passed where a dict/object was expected?
**Underlying design issue**: Import conflict where async version of `get_env()` is being imported instead of synchronous one, OR `get_env()` function was changed to async without updating call sites.

### Why 4: Why was the calling pattern changed?
**Process/change that introduced it**: Recent SSOT consolidation efforts introduced async version of `get_env()` or caused import conflict during shared infrastructure changes.

### Why 5: Why wasn't this caught in testing?
**Root systemic cause**: Test suite lacks comprehensive WebSocket integration tests for staging environment. Error only manifests in E2E testing detection logic paths not covered by unit tests.

## Code Analysis
**Location**: `netra_backend/app/routes/websocket.py` lines 213-217  
**Pattern**: Multiple calls to `get_env().get("KEY", "default")` in E2E testing detection  
**Root Issue**: `get_env()` returning coroutine instead of `IsolatedEnvironment` instance

## Recommended Fix Approach
1. **Immediate**: Verify `shared.isolated_environment.get_env()` is synchronous
2. **Check imports**: Ensure no async `get_env()` imported by mistake  
3. **Add await**: If `get_env()` needs to be async, add `await` to all calls
4. **Test coverage**: Add WebSocket integration tests for E2E detection logic

## Test Plan Summary
**Test Strategy**: Four-layer testing approach (Unit → Integration → E2E → Staging)
**Focus**: Immediate detection of coroutine/environment access regressions
**Compliance**: Real authentication, real services, fail-hard design
**Categories**: 
- Unit tests for environment function behavior
- Integration tests for WebSocket+auth flows  
- E2E tests for complete chat business value
- Staging validation with load testing

## Working Log
- [✓] Five Whys analysis completed
- [✓] Test plan created (comprehensive 4-layer strategy)
- [✓] GitHub issue created: https://github.com/netra-systems/netra-apex/issues/133
- [ ] Code inspection at line 557 completed  
- [ ] Fix implemented and tested
- [ ] System stability validated