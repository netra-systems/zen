# Netra AI Platform - Test Report

**Generated:** 2025-08-21T11:09:13.275886  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 69
- **Passed:** 11 
- **Failed:** 58
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 0 | 0 | 0 | 0 | 0 | 5.12s | [FAILED] |
| Frontend  | 69 | 11 | 58 | 0 | 0 | 55.10s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 60.22s
- **Exit Code:** 4

### Backend Configuration
```
--category integration -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category integration
```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: integration
  Parallel: 4
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini integration_tests netra_backend/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 4.36s
================================================================================

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\monitoring.py:68: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "system_start_time": datetime.utcnow(),
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\monitoring.py:68: DeprecationWarning: datetime.datetime.utcnow() is deprecated and scheduled for removal in a future version. Use timezone-aware objects to represent datetimes in UTC: datetime.datetime.now(datetime.UTC).
  "system_start_time": datetime.utcnow(),
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:59: in <module>
    from netra_backend.app.routes.mcp.main import app
netra_backend\app\routes\mcp\__init__.py:8: in <module>
    from netra_backend.app.routes.mcp.main import router
netra_backend\app\routes\mcp\main.py:25: in <module>
    from netra_backend.app.routes.mcp.handlers import MCPHandlers
netra_backend\app\routes\mcp\handlers.py:11: in <module>
    from netra_backend.app.routes.mcp.handlers_server import handle_server_info
netra_backend\app\routes\mcp\handlers_server.py:4: in <module>
    from netra_backend.app.services.mcp_service import MCPService
netra_backend\app\services\mcp_service.py:20: in <module>
    from netra_backend.app.services.agent_service import AgentService
netra_backend\app\services\agent_service.py:8: in <module>
    from netra_backend.app.services.agent_service_core import AgentService
netra_backend\app\services\agent_service_core.py:13: in <module>
    from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent as Supervisor
netra_backend\app\agents\supervisor_consolidated.py:24: in <module>
    from netra_backend.app.agents.base.executor import BaseExecutionEngine
netra_backend\app\agents\base\executor.py:26: in <module>
    from netra_backend.app.agents.base.reliability import ReliabilityManager
netra_backend\app\agents\base\reliability.py:33: in <module>
    from netra_backend.app.agents.base.rate_limiter import RateLimiter
netra_backend\app\agents\base\rate_limiter.py:17: in <module>
    from netra_backend.app.websocket.rate_limiter import RateLimiter as CoreRateLimiter
netra_backend\app\websocket\__init__.py:13: in <module>
    from netra_backend.app.websocket.heartbeat_manager import HeartbeatManager
netra_backend\app\websocket\heartbeat_manager.py:13: in <module>
    from netra_backend.app.services.synthetic_data.error_handler import ErrorHandler as WebSocketErrorHandler
netra_backend\app\services\synthetic_data\__init__.py:5: in <module>
    from netra_backend.app.services.synthetic_data.core_service import SyntheticDataService, synthetic_data_service
netra_backend\app\services\synthetic_data\core_service.py:9: in <module>
    from netra_backend.app.services.synthetic_data.synthetic_data_service_main import SyntheticDataService, synthetic_data_service
netra_backend\app\services\synthetic_data\synthetic_data_service_main.py:7: in <module>
    from netra_backend.app.services.synthetic_data.generation_coordinator import GenerationCoordinator
netra_backend\app\services\synthetic_data\generation_coordinator.py:8: in <module>
    from netra_backend.app.services.synthetic_data.core_service_base import CoreServiceBase
netra_backend\app\services\synthetic_data\core_service_base.py:13: in <module>
    from netra_backend.app.services.synthetic_data.job_manager import JobManager
netra_backend\app\services\synthetic_data\job_manager.py:11: in <module>
    from netra_backend.app.services.websocket.ws_manager import manager
netra_backend\app\services\websocket\ws_manager.py:47: in __getattr__
    mgr, _, _, _ = _lazy_import()
                   ^^^^^^^^^^^^^^
netra_backend\app\services\websocket\ws_manager.py:29: in _lazy_import
    from netra_backend.app.ws_manager import (
netra_backend\app\ws_manager.py:245: in <module>
    manager = get_manager()
              ^^^^^^^^^^^^^
netra_backend\app\ws_manager.py:241: in get_manager
    _manager = WebSocketManager()
               ^^^^^^^^^^^^^^^^^^
netra_backend\app\ws_manager.py:38: in __new__
    cls._instance._initialize_unified_delegation()
netra_backend\app\ws_manager.py:45: in _initialize_unified_delegation
    self._unified_manager = get_unified_manager()
                            ^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\unified\manager.py:410: in get_unified_manager
    _unified_manager = UnifiedWebSocketManager()
                       ^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\unified\manager.py:65: in __init__
    self._initialize_core_components()
netra_backend\app\websocket\unified\manager.py:73: in _initialize_core_components
    self.connection_manager = ConnectionManager()
                              ^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection.py:56: in __init__
    self._modern_manager = ModernConnectionManager()
                           ^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection_manager.py:37: in __init__
    self.orchestrator = ConnectionExecutionOrchestrator()
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection_executor.py:284: in __init__
    self.executor = ConnectionExecutor()
                    ^^^^^^^^^^^^^^^^^^^^
netra_backend\app\websocket\connection_executor.py:29: in __init__
    self._initialize_components()
netra_backend\app\websocket\connection_executor.py:34: in _initialize_components
    self._initialize_execution_engine()
netra_backend\app\websocket\connection_executor.py:44: in _initialize_execution_engine
    from netra_backend.app.agents.base.executor import BaseExecutionEngine
E   ImportError: cannot import name 'BaseExecutionEngine' from partially initialized module 'netra_backend.app.agents.base.executor' (most likely due to a circular import) (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\agents\base\executor.py)

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)

================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 1
================================================================================

Cleaning up test processes...

FAIL __tests__/integration/websocket-complete-refactored.test.tsx (53.098 s)
  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should track real connection state transitions with history

    Connection timeout

    [0m [90m 167 |[39m           resolve()[33m;[39m
     [90m 168 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 169 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m         } [36melse[39m {
     [90m 171 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 172 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should measure real connection performance

    Connection timeout

    [0m [90m 167 |[39m           resolve()[33m;[39m
     [90m 168 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 169 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m         } [36melse[39m {
     [90m 171 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 172 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Error Handling › should handle real connection errors with proper state transitions

    expect(received).toBe(expected) // Object.is equality

    Expected: "error"
    Received: "connected"

    Ignored nodes: comments, script, style
    [36m<html>[39m
      [36m<head />[39m
      [36m<body>[39m
        [36m<div>[39m
          [36m<div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"ws-connecting"[39m
            [36m>[39m
              [0mfalse[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"ws-connected"[39m
            [36m>[39m
              [0mfalse[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"ws-disconnected"[39m
            [36m>[39m
              [0mtrue[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"ws-error"[39m
            [36m>[39m
              [0mfalse[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"ws-reconnecting"[39m
            [36m>[39m
              [0mfalse[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"metrics-sent"[39m
            [36m>[39m
              [0m0[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"metrics-received"[39m
            [36m>[39m
              [0m0[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"metrics-queued"[39m
            [36m>[39m
              [0m0[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"metrics-failed"[39m
            [36m>[39m
              [0m0[0m
            [36m</div>[39m
            [36m<div[39m
              [33mdata-testid[39m=[32m"metrics-large"[39m
            [36m>[39m
              [0m0[0m
            [36m</div>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-connecting"[39m
            [36m>[39m
              [0mStart Connecting[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-connected"[39m
            [36m>[39m
              [0mConnected[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-disconnected"[39m
            [36m>[39m
              [0mDisconnected[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-error"[39m
            [36m>[39m
              [0mError[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-reconnecting"[39m
            [36m>[39m
              [0mReconnecting[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-send"[39m
            [36m>[39m
              [0mSend Message[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-receive"[39m
            [36m>[39m
              [0mReceive Message[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-queue"[39m
            [36m>[39m
              [0mQueue Message[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-fail"[39m
            [36m>[39m
              [0mFail Message[0m
            [36m</button>[39m
            [36m<button[39m
              [33mdata-testid[39m=[32m"btn-large"[39m
            [36m>[39m
              [0mLarge Message[0m
            [36m</button>[39m
          [36m</div>[39m
        [36m</div>[39m
      [36m</body>[39m
    [36m</html>[39m

    [0m [90m  98 |[39m       
     [90m  99 |[39m       [36mawait[39m waitFor(() [33m=>[39m {
    [31m[1m>[22m[39m[90m 100 |[39m         expect(wsManager[33m.[39mgetConnectionState())[33m.[39mtoBe([32m'error'[39m)[33m;[39m
     [90m     |[39m                                                [31m[1m^[22m[39m
     [90m 101 |[39m       })[33m;[39m
     [90m 102 |[39m       
     [90m 103 |[39m       expect(wsManager[33m.[39mgetConnectionHistory())[33m.[39mtoContainEqual([0m

      at toBe (__tests__/integration/websocket-lifecycle.test.tsx:100:48)
      at runWithExpensiveErrorDiagnosticsDisabled (node_modules/@testing-library/dom/dist/config.js:47:12)
      at checkCallback (node_modules/@testing-library/dom/dist/wait-for.js:124:77)
      at checkRealTimersCallback (node_modules/@testing-library/dom/dist/wait-for.js:118:16)
      at Timeout.task [as _onTimeout] (node_modules/jsdom/lib/jsdom/browser/Window.js:579:19)

  ● WebSocket Connection Lifecycle Tests › Error Handling › should handle network disconnections gracefully

    Connection timeout

    [0m [90m 167 |[39m           resolve()[33m;[39m
     [90m 168 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 169 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m         } [36melse[39m {
     [90m 171 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 172 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Reconnection Scenarios › should handle real reconnection with timing simulation

    Connection timeout

    [0m [90m 167 |[39m           resolve()[33m;[39m
     [90m 168 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 169 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m         } [36melse[39m {
     [90m 171 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 172 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/...(truncated)
```

## 5. Error Details

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (53.098 s)
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (53.098 s)

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
