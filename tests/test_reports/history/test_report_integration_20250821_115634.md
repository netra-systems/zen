# Netra AI Platform - Test Report

**Generated:** 2025-08-21T11:56:34.162105  
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
| Backend   | 0 | 0 | 0 | 0 | 0 | 6.63s | [FAILED] |
| Frontend  | 69 | 11 | 58 | 0 | 0 | 58.40s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 65.03s
- **Exit Code:** 15

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
[FAIL] TESTS FAILED with exit code 4 after 5.74s
================================================================================

C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(
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
netra_backend\app\core\app_factory_route_imports.py:124: in import_all_route_modules
    factory_routers = import_factory_routers()
                      ^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:99: in import_factory_routers
    status_routers = _import_factory_status_routers()
                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
netra_backend\app\core\app_factory_route_imports.py:106: in _import_factory_status_routers
    from netra_backend.app.routes.factory_status import router as factory_status_router
netra_backend\app\routes\factory_status\__init__.py:5: in <module>
    from netra_backend.app.routes.factory_status.router import router
netra_backend\app\routes\factory_status\router.py:16: in <module>
    from netra_backend.app.routes.database_monitoring.dashboard_routes import get_dashboard_summary_handler, test_factory_status_handler
E   ImportError: cannot import name 'get_dashboard_summary_handler' from 'netra_backend.app.routes.database_monitoring.dashboard_routes' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\netra_backend\app\routes\database_monitoring\dashboard_routes.py)

```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> node run-jest.js --config jest.config.simple.cjs --forceExit --detectOpenHandles --testMatch **/__tests__/integration/**/*.test.[jt]s?(x)


FAIL __tests__/integration/websocket-complete-refactored.test.tsx (56.111 s)
  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should handle complete connection lifecycle with real timing

    expect(received).toBe(expected) // Object.is equality

    Expected: "connected"
    Received: "disconnected"

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

    [0m [90m 47 |[39m       [90m// Wait for real connection[39m
     [90m 48 |[39m       [36mawait[39m waitFor(() [33m=>[39m {
    [31m[1m>[22m[39m[90m 49 |[39m         expect(wsManager[33m.[39mgetConnectionState())[33m.[39mtoBe([32m'connected'[39m)[33m;[39m
     [90m    |[39m                                                [31m[1m^[22m[39m
     [90m 50 |[39m       }[33m,[39m { timeout[33m:[39m [35m2000[39m })[33m;[39m
     [90m 51 |[39m
     [90m 52 |[39m       [90m// Verify real connection state[39m[0m

      at toBe (__tests__/integration/websocket-lifecycle.test.tsx:49:48)
      at runWithExpensiveErrorDiagnosticsDisabled (node_modules/@testing-library/dom/dist/config.js:47:12)
      at checkCallback (node_modules/@testing-library/dom/dist/wait-for.js:124:77)
      at checkRealTimersCallback (node_modules/@testing-library/dom/dist/wait-for.js:118:16)
      at Timeout.task [as _onTimeout] (node_modules/jsdom/lib/jsdom/browser/Window.js:579:19)

  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should track real connection state transitions with history

    Connection timeout

    [0m [90m 167 |[39m       
     [90m 168 |[39m       [36mconst[39m checkConnection [33m=[39m () [33m=>[39m {
    [31m[1m>[22m[39m[90m 169 |[39m         [36mif[39m ([36mthis[39m[33m.[39mstateManager[33m.[39mgetState() [33m===[39m [32m'connected'[39m) {
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
     [90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should measure real connection performance

    Connection timeout

    [0m [90m 167 |[39m       
     [90m 168 |[39m       [36mconst[39m checkConnection [33m=[39m () [33m=>[39m {
    [31m[1m>[22m[39m[90m 169 |[39m         [36mif[39m ([36mthis[39m[33m.[39mstateManager[33m.[39mgetState() [33m===[39m [32m'connected'[39m) {
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
     [90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Error Handling › should handle network disconnections gracefully

    Connection timeout

    [0m [90m 167 |[39m       
     [90m 168 |[39m       [36mconst[39m checkConnection [33m=[39m () [33m=>[39m {
    [31m[1m>[22m[39m[90m 169 |[39m         [36mif[39m ([36mthis[39m[33m.[39mstateManager[33m.[39mgetState() [33m===[39m [32m'connected'[39m) {
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
     [90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Reconnection Scenarios › should handle real reconnection with timing simulation

    Connection timeout

    [0m [90m 167 |[39m       
     [90m 168 |[39m       [36mconst[39m checkConnection [33m=[39m () [33m=>[39m {
    [31m[1m>[22m[39m[90m 169 |[39m         [36mif[39m ([36mthis[39m[33m.[39mstateManager[33m.[39mgetState() [33m===[39m [32m'connected'[39m) {
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
     [90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:169:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Reconnection Scenarios › should test real WebSocket reconnection strategies

    Connection timeout

    [0m [90m 167 |[39m       
     [90m 168 |[39m       [36mconst[39m checkConnection [33m=[39m () [33m=>[39m {
    [31m[1m>[22m[39m[90m 169 |[39m         [36mif[39m ([36mthis[39m[33m.[39mstateManager[33m.[39mgetState() [33m===[39m [32m'connected'[39m) {
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [3...(truncated)
```

## 5. Error Details

### Frontend Errors
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (56.111 s)
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (56.111 s)

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
