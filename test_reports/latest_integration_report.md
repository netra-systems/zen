# Netra AI Platform - Test Report

**Generated:** 2025-08-21T12:15:13.441118  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 73
- **Passed:** 10 
- **Failed:** 59
- **Skipped:** 0
- **Errors:** 4

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 4 | 0 | 0 | 0 | 4 | 16.04s | [FAILED] |
| Frontend  | 69 | 10 | 59 | 0 | 0 | 57.83s | [FAILED] |

## 3. Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 73.87s
- **Exit Code:** 2

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
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/integration netra_backend/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.5.3', 'asyncio': '1.1.0', 'cov': '6.2.1', 'mock': '3.14.1', 'xdist': '3.8.0', 'langsmith': '0.4.10', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'timeout': '2.4.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.5.3, asyncio-1.1.0, cov-6.2.1, mock-3.14.1, xdist-3.8.0, langsmith-0.4.10, html-4.1.1, json-report-1.5.0, metadata-3.1.1, timeout-2.4.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
created: 4/4 workers

================================================================================
BAD TEST DETECTION REPORT
================================================================================

Total Bad Tests Detected: 0
Total Test Runs Analyzed: 129

================================================================================


=================================== ERRORS ====================================
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
'l3' not found in `markers` configuration option
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
'l3' not found in `markers` configuration option
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
'l3' not found in `markers` configuration option
[31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
'l3' not found in `markers` configuration option
[36m[1m=========================== short test summary info ===========================[0m
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
[31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 4 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m============================== [31m[1m4 errors[0m[31m in 8.87s[0m[31m ==============================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 15.17s
================================================================================

C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataSample" shadows an attribute in parent "BaseModel"
  warnings.warn(
C:\Users\antho\miniconda3\Lib\site-packages\pydantic\_internal\_fields.py:198: UserWarning: Field name "schema" in "DataCatalog" shadows an attribute in parent "BaseModel"
  warnings.warn(

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

FAIL __tests__/integration/websocket-complete-refactored.test.tsx (55.924 s)
  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should track real connection state transitions with history

    Connection timeout

    [0m [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 173 |[39m         } [36melse[39m {
     [90m 174 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 175 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:172:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Connection Establishment › should measure real connection performance

    Connection timeout

    [0m [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 173 |[39m         } [36melse[39m {
     [90m 174 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 175 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:172:18)
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

    [0m [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 173 |[39m         } [36melse[39m {
     [90m 174 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 175 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:172:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/browser/Window.js:613:9

  ● WebSocket Connection Lifecycle Tests › Reconnection Scenarios › should handle real reconnection with timing simulation

    Connection timeout

    [0m [90m 170 |[39m           resolve()[33m;[39m
     [90m 171 |[39m         } [36melse[39m [36mif[39m ([33mDate[39m[33m.[39mnow() [33m-[39m startTime [33m>[39m timeoutMs) {
    [31m[1m>[22m[39m[90m 172 |[39m           reject([36mnew[39m [33mError[39m([32m'Connection timeout'[39m))[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 173 |[39m         } [36melse[39m {
     [90m 174 |[39m           [90m// Use queueMicrotask for better React synchronization[39m
     [90m 175 |[39m           queueMicrotask(checkConnection)[33m;[39m[0m

      at checkConnection (__tests__/helpers/websocket-test-manager.ts:172:18)
      at invokeTheCallbackFunction (node_modules/jsdom/lib/jsdom/living/generated/Function.js:19:26)
      at node_modules/jsdom/lib/jsdom/...(truncated)
```

## 5. Error Details

### Backend Errors
- =================================== ERRORS ====================================
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
- [31m[1m_ ERROR collecting netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py _[0m
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
- [31mERROR[0m netra_backend/tests/integration/critical_paths/test_agent_collaboration_workflow_l3.py - Failed: 'l3' not found in `markers` configuration option
- [FAIL] TESTS FAILED with exit code 2 after 15.17s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (55.924 s)
- FAIL __tests__/integration/websocket-complete-refactored.test.tsx (55.924 s)

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
