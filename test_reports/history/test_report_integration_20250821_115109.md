# Netra AI Platform - Test Report

**Generated:** 2025-08-21T11:46:23.074461  
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
| Backend   | 0 | 0 | 0 | 0 | 0 | 8.45s | [FAILED] |
| Frontend  | 69 | 11 | 58 | 0 | 0 | 55.48s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 63.93s
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
  Coverage: enabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini integration_tests netra_backend/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services
================================================================================
================================================================================
[FAIL] TESTS FAILED with exit code 4 after 7.63s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================

2025-08-21 11:45:25.624 | ERROR    | logging:handle:1028 | Error loading blocked IPs config: [Errno 2] No such file or directory: 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\netra_backend\\config\\blocked_ips.json'
ImportError while loading conftest 'C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\tests\conftest.py'.
netra_backend\tests\conftest.py:59: in <module>
    from netra_backend.app.main import app
netra_backend\app\main.py:93: in <module>
    app = create_app()
          ^^^^^^^^^^^^
netra_backend\app\core\app_factory.py:127: in create_app
    _configure_app_routes(app)
netra_backend\app\core\app_factory.py:140: in _configure_app_routes
    register_api_routes(app)
netra_backend\app\core\app_factory.py:97: in register_api_routes
    _import_and_register_routes(app)
netra_backend\app\core\app_factory.py:102: in _import_and_register_routes
    route_modules = import_all_route_modules()
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:122: in import_all_route_modules
    basic_modules = import_basic_route_modules()
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:5: in import_basic_route_modules
    route_imports = _import_core_routes()
                    ^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:11: in _import_core_routes
    from netra_backend.app.routes import (supply, generation, admin, references, health,
netra_backend\app\routes\unified_tools\__init__.py:5: in <module>
    from netra_backend.app.routes.unified_tools.router import router
netra_backend\app\routes\unified_tools\router.py:15: in <module>
    from netra_backend.app.routes.unified_tools.tool_listing import gather_tool_data, build_tool_availability_response
netra_backend\app\routes\unified_tools\tool_listing.py:8: in <module>
    from netra_backend.app.routes.unified_tools.models import ToolAvailabilityResponse
E   ModuleNotFoundError: No module named 'netra_backend.app.routes.unified_tools.models'

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

FAIL __tests__/integration/websocket-complete-refactored.test.tsx (53.294 s)
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
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (53.294 s)
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (53.294 s)

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
