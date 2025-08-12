# Netra AI Platform - Test Report

**Generated:** 2025-08-12T12:23:46.837415  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  
**Purpose:** Feature validation, API testing

## Test Summary

**Total Tests:** 131  
**Passed:** 81  
**Failed:** 49  
**Skipped:** 0  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 8 | 4 | 3 | 0 | 1 | 32.30s | [FAILED] |
| Frontend  | 123 | 77 | 46 | 0 | 0 | 26.81s | [FAILED] |

## Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 59.11s
- **Exit Code:** 2

### Backend Configuration
```
--category integration -v --coverage --fail-fast --parallel=4 -m not real_services
```

### Frontend Configuration
```
--category integration
```

## Test Output

### Backend Output
```
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: integration
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: development

Running command:
  pytest integration_tests app/tests/routes -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [85 items]

scheduling tests via LoadScheduling

integration_tests/test_generation_service.py::test_save_and_get_corpus 
app/tests/routes/test_apex_optimizer_agent_route.py::test_apex_optimizer_agent[I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.] 
integration_tests/test_health.py::test_ready_endpoint_clickhouse_failure 
integration_tests/test_app.py::test_read_main 
[gw2][36m [  1%] [0m[31mERROR[0m integration_tests/test_health.py::test_ready_endpoint_clickhouse_failure 
[gw1][36m [  2%] [0m[32mPASSED[0m integration_tests/test_generation_service.py::test_save_and_get_corpus 
integration_tests/test_generation_service.py::test_run_synthetic_data_generation_job_e2e 
[gw1][36m [  3%] [0m[31mFAILED[0m integration_tests/test_generation_service.py::test_run_synthetic_data_generation_job_e2e 
[gw3][36m [  4%] [0m[32mPASSED[0m app/tests/routes/test_apex_optimizer_agent_route.py::test_apex_optimizer_agent[I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.] 
app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_endpoint_requires_authentication 
[gw3][36m [  5%] [0m[32mPASSED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_endpoint_requires_authentication 
app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_role_verification 
[gw3][36m [  7%] [0m[32mPASSED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_role_verification 
app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_user_management 
[gw3][36m [  8%] [0m[31mFAILED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_user_management 
[gw0] node down: Not properly terminated
[gw0][36m [  9%] [0m[31mFAILED[0m integration_tests/test_app.py::test_read_main 

replacing crashed worker gw0

=================================== ERRORS ====================================
[31m[1m__________ ERROR at setup of test_ready_endpoint_clickhouse_failure ___________[0m
[gw2] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
file C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\integration_tests\test_health.py, line 37
  def test_ready_endpoint_clickhouse_failure(client: TestClient):
E       fixture 'client' not found
>       available fixtures: _session_faker, anyio_backend, anyio_backend_name, anyio_backend_options, cache, capfd, capfdbinary, caplog, capsys, capsysbinary, capteesys, class_mocker, cleanup_dependency_overrides, cov, doctest_namespace, event_loop, extra, extras, faker, free_tcp_port, free_tcp_port_factory, free_udp_port, free_udp_port_factory, include_metadata_in_junit_xml, json_metadata, metadata, mocker, module_mocker, monkeypatch, no_cover, package_mocker, pytestconfig, record_property, record_testsuite_property, record_xml_attribute, recwarn, session_mocker, testrun_uid, tmp_path, tmp_path_factory, tmpdir, tmpdir_factory, unused_tcp_port, unused_tcp_port_factory, unused_udp_port, unused_udp_port_factory, worker_id
>       use 'pytest --fixtures [testpath]' for help on them.

C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\integration_tests\test_health.py:37
================================== FAILURES ===================================
[31m[1m_________________ test_run_synthetic_data_generation_job_e2e __________________[0m
[gw1] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
[1m[31mintegration_tests\test_generation_service.py[0m:178: in test_run_synthetic_data_generation_job_e2e
    [0m[94massert[39;49;00m job_status [95mis[39;49;00m [95mnot[39;49;00m [94mNone[39;49;00m[90m[39;49;00m
[1m[31mE   assert None is not None[0m
---------------------------- Captured stderr call -----------------------------
C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\integration_tests\test_generation_service.py:153: RuntimeWarning: coroutine 'JobStore.set' was never awaited
  job_store.set("test", {})
RuntimeWarning: Enable tracemalloc to get the object allocation traceback
---------------------------- Captured log teardown ----------------------------
[35mDEBUG   [0m asyncio:proactor_events.py:634 Using proactor: IocpProactor
[31m[1m__________________ TestAdminRoute.test_admin_user_management __________________[0m
[gw3] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
[1m[31mapp\tests\routes\test_api_routes_21_30.py[0m:45: in test_admin_user_management
    [0m[94mwith[39;49;00m patch([33m'[39;49;00m[33mapp.services.user_service.get_all_users[39;49;00m[33m'[39;49;00m) [94mas[39;49;00m mock_get:[90m[39;49;00m
[1m[31m..\..\..\..\miniconda3\Lib\unittest\mock.py[0m:1458: in __enter__
    [0moriginal, local = [96mself[39;49;00m.get_original()[90m[39;49;00m
                      ^^^^^^^^^^^^^^^^^^^[90m[39;49;00m
[1m[31m..\..\..\..\miniconda3\Lib\unittest\mock.py[0m:1431: in get_original
    [0m[94mraise[39;49;00m [96mAttributeError[39;49;00m([90m[39;49;00m
[1m[31mE   AttributeError: <module 'app.services.user_service' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\user_service.py'> does not have the attribute 'get_all_users'[0m
----------------------------- Captured log setup ------------------------------
[35mDEBUG   [0m asyncio:proactor_events.py:634 Using proactor: IocpProactor
---------------------------- Captured log teardown ----------------------------
[35mDEBUG   [0m asyncio:proactor_events.py:634 Using proactor: IocpProactor
[31m[1m________________________ integration_tests/test_app.py ________________________[0m
[gw0] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
worker 'gw0' crashed while running 'integration_tests/test_app.py::test_read_main'
[36m[1m=========================== short test summary info ===========================[0m
[31mFAILED[0m integration_tests/test_generation_service.py::[1mtest_run_synthetic_data_generation_job_e2e[0m - assert None is not None
[31mFAILED[0m app/tests/routes/test_api_routes_21_30.py::[1mTestAdminRoute::test_admin_user_management[0m - AttributeError: <module 'app.services.user_service' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\user_service.py'> does not have the attribute 'get_all_users'
[31mFAILED[0m integration_tests/test_app.py::[1mtest_read_main[0m
[31mERROR[0m integration_tests/test_health.py::[1mtest_ready_endpoint_clickhouse_failure[0m
[31m!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 4 failures !!!!!!!!!!!!!!!!!!!!!!!!!![0m
!!!!!!!!!!!! xdist.dsession.Interrupted: stopping after 1 failures !!!!!!!!!!!!
[31m==================== [31m[1m3 failed[0m, [32m4 passed[0m, [31m[1m1 error[0m[31m in 23.38s[0m[31m ====================[0m
================================================================================
[FAIL] TESTS FAILED with exit code 2 after 31.45s
[Coverage] Coverage Report: reports/coverage/html/index.html
================================================================================


```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest __tests__/integration __tests__/api

================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- __tests__/integration __tests__/api
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 1
================================================================================

FAIL __tests__/integration/critical-integration.test.tsx
  ● Console

    console.warn
      Performance degradation: api_latency = 1500ms (threshold: 1000ms)

    [0m [90m 111 |[39m       [36mreturn[39m[33m;[39m
     [90m 112 |[39m     }
    [31m[1m>[22m[39m[90m 113 |[39m     originalWarn[33m.[39mcall(console[33m,[39m [33m...[39margs)[33m;[39m
     [90m     |[39m                  [31m[1m^[22m[39m
     [90m 114 |[39m   }[33m;[39m
     [90m 115 |[39m })[33m;[39m
     [90m 116 |[39m[0m

      at console.call (jest.setup.ts:113:18)
      at warn (__tests__/integration/critical-integration.test.tsx:929:19)
      at Object.checkPerformance (__tests__/integration/critical-integration.test.tsx:936:22)

    console.log
      Flushed notification: { type: 'info', message: 'Offline notification 1' }

      at log (__tests__/integration/critical-integration.test.tsx:1063:19)

    console.log
      Flushed notification: { type: 'warning', message: 'Offline notification 2' }

      at log (__tests__/integration/critical-integration.test.tsx:1063:19)

  ● Critical Frontend Integration Tests › 1. WebSocket Provider Integration › should integrate WebSocket with authentication state

    TypeError: Cannot destructure property 'token' of '(0 , _react.useContext)(...)' as it is undefined.

    [0m [90m 28 |[39m
     [90m 29 |[39m [36mexport[39m [36mconst[39m [33mWebSocketProvider[39m [33m=[39m ({ children }[33m:[39m [33mWebSocketProviderProps[39m) [33m=>[39m {
    [31m[1m>[22m[39m[90m 30 |[39m   [36mconst[39m { token } [33m=[39m useContext([33mAuthContext[39m)[33m![39m[33m;[39m
     [90m    |[39m           [31m[1m^[22m[39m
     [90m 31 |[39m   [36mconst[39m [status[33m,[39m setStatus] [33m=[39m useState[33m<[39m[33mWebSocketStatus[39m[33m>[39m([32m'CLOSED'[39m)[33m;[39m
     [90m 32 |[39m   [36mconst[39m [messages[33m,[39m setMessages] [33m=[39m useState[33m<[39m[33mWebSocketMessage[39m[][33m>[39m([])[33m;[39m
     [90m 33 |[39m[0m

      at token (providers/WebSocketProvider.tsx:30:11)
      at Object.react-stack-bottom-frame (node_modules/react-dom/cjs/react-dom-client.development.js:23863:20)
      at renderWithHooks (node_modules/react-dom/cjs/react-dom-client.development.js:5529:22)
      at updateFunctionComponent (node_modules/react-dom/cjs/react-dom-client.development.js:8897:19)
      at beginWork (node_modules/react-dom/cjs/react-dom-client.development.js:10522:18)
      at runWithFiberInDEV (node_modules/react-dom/cjs/react-dom-client.development.js:1522:13)
      at performUnitOfWork (node_modules/react-dom/cjs/react-dom-client.development.js:15140:22)
      at workLoopSync (node_modules/react-dom/cjs/react-dom-client.development.js:14956:41)
      at renderRootSync (node_modules/react-dom/cjs/react-dom-client.development.js:14936:11)
      at performWorkOnRoot (node_modules/react-dom/cjs/react-dom-client.development.js:14462:44)
      at performWorkOnRootViaSchedulerTask (node_modules/react-dom/cjs/react-dom-client.development.js:16216:7)
      at flushActQueue (node_modules/react/cjs/react.development.js:566:34)
      at process.env.NODE_ENV.exports.act (node_modules/react/cjs/react.development.js:859:10)
      at node_modules/@testing-library/react/dist/act-compat.js:47:25
      at renderRoot (node_modules/@testing-library/react/dist/pure.js:190:26)
      at render (node_modules/@testing-library/react/dist/pure.js:292:10)
      at Object.<anonymous> (__tests__/integration/critical-integration.test.tsx:83:13)

  ● Critical Frontend Integration Tests › 1. WebSocket Provider Integration › should reconnect WebSocket when authentication changes

    TypeError: Cannot destructure property 'token' of '(0 , _react.useContext)(...)' as it is undefined.

    [0m [90m 28 |[39m
     [90m 29 |[39m [36mexport[39m [36mconst[39m [33mWebSocketProvider[39m [33m=[39m ({ children }[33m:[39m [33mWebSocketProviderProps[39m) [33m=>[39m {
    [31m[1m>[22m[39m[90m 30 |[39m   [36mconst[39m { token } [33m=[39m useContext([33mAuthContext[39m)[33m![39m[33m;[39m
     [90m    |[39m           [31m[1m^[22m[39m
     [90m 31 |[39m   [36mconst[39m [status[33m,[39m setStatus] [33m=[39m useState[33m<[39m[33mWebSocketStatus[39m[33m>[39m([32m'CLOSED'[39m)[33m;[39m
     [90m 32 |[39m   [36mconst[39m [messages[33m,[39m setMessages] [33m=[39m useState[33m<[39m[33mWebSocketMessage[39m[][33m>[39m([])[33m;[39m
     [90m 33 |[39m[0m

      at token (providers/WebSocketProvider.tsx:30:11)
      at Object.react-stack-bottom-frame (node_modules/react-dom/cjs/react-dom-client.development.js:23863:20)
      at renderWithHooks (node_modules/react-dom/cjs/react-dom-client.development.js:5529:22)
      at updateFunctionComponent (node_modules/react-dom/cjs/react-dom-client.development.js:8897:19)
      at beginWork (node_modules/react-dom/cjs/react-dom-client.development.js:10522:18)
      at runWithFiberInDEV (node_modules/react-dom/cjs/react-dom-client.development.js:1522:13)
      at performUnitOfWork (node_modules/react-dom/cjs/react-dom-client.development.js:15140:22)
      at workLoopSync (node_modules/react-dom/cjs/react-dom-client.development.js:14956:41)
      at renderRootSync (node_modules/react-dom/cjs/react-dom-client.development.js:14936:11)
      at performWorkOnRoot (node_modules/react-dom/cjs/react-dom-client.development.js:14462:44)
      at performWorkOnRootViaSchedulerTask (node_modules/react-dom/cjs/react-dom-client.development.js:16216:7)
      at flushActQueue (node_modules/react/cjs/react.development.js:566:34)
      at process.env.NODE_ENV.exports.act (node_modules/react/cjs/react.development.js:859:10)
      at node_modules/@testing-library/react/dist/act-compat.js:47:25
      at renderRoot (node_modules/@testing-library/react/dist/pure.js:190:26)
      at render (node_modules/@testing-library/react/dist/pure.js:292:10)
      at Object.<anonymous> (__tests__/integration/critical-integration.test.tsx:110:35)

  ● Critical Frontend Integration Tests › 2. Agent Provider Integration › should coordinate agent state with WebSocket messages

    TypeError: Cannot destructure property 'token' of '(0 , _react.useContext)(...)' as it is undefined.

    [0m [90m 28 |[39m
     [90m 29 |[39m [36mexport[39m [36mconst[39m [33mWebSocketProvider[39m [33m=[39m ({ children }[33m:[39m [33mWebSocketProviderProps[39m) [33m=>[39m {
    [31m[1m>[22m[39m[90m 30 |[39m   [36mconst[39m { token } [33m=[39m useContext([33mAuthContext[39m)[33m![39m[33m;[39m
     [90m    |[39m           [31m[1m^[22m[39m
     [90m 31 |[39m   [36mconst[39m [status[33m,[39m setStatus] [33m=[39m useState[33m<[39m[33mWebSocketStatus[39m[33m>[39m([32m'CLOSED'[39m)[33m;[39m
     [90m 32 |[39m   [36mconst[39m [messages[33m,[39m setMessages] [33m=[39m useState[33m<[39m[33mWebSocketMessage[39m[][33m>[39m([])[33m;[39m
     [90m 33 |[39m[0m

      at token (providers/WebSocketProvider.tsx:30:11)
      at Object.react-stack-bottom-frame (node_modules/react-dom/cjs/react-dom-client.development.js:23863:20)
      at renderWithHooks (node_modules/react-dom/cjs/react-dom-client.development.js:5529:22)
      at updateFunctionComponent (node_modules/react-dom/cjs/react-dom-client.development.js:8897:19)
      at beginWork (node_modules/react-dom/cjs/react-dom-client.development.js:10522:18)
      at runWithFiberInDEV (node_modules/react-dom/cjs/react-dom-client.development.js:1522:13)
      at performUnitOfWork (node_modules/react-dom/cjs/react-dom-client.development.js:15140:22)
      at workLoopSync (node_modules/react-dom/cjs/react-dom-client.development.js:14956:41)
      at renderRootSync (node_modules/react-dom/cjs/react-dom-client.development.js:14936:11)
      at performWorkOnRoot (node_modules/react-dom/cjs/react-dom-client.development.js:14462:44)
      at performWorkOnRootViaSchedulerTask (node_modules/react-dom/cjs/react-dom-client.development.js:16216:7)
      at flushActQueue (node_modules/react/cjs/react.development.js:566:34)
      at process.env.NODE_ENV.exports.act (node_modules/react/cjs/react.development.js:859:10)
      at node_modules/@testing-library/react/dist/act-compat.js:47:25
      at renderRoot (node_modules/@testing-library/react/dist/pure.js:190:26)
      at render (node_modules/@testing-library/react/dist/pure.js:292:10)
      at Object.<anonymous> (__tests__/integration/critical-integration.test.tsx:142:35)

  ● Critical Frontend Integration Tests › 2. Agent Provider Integration › should sync agent reports with chat messages

    TypeError: Cannot destructure property 'token' of '(0 , _react.useContext)(...)' as it is undefined.

    [0m [90m 28 |[39m
     [90m 29 |[39m [36mexport[39m [36mconst[39m [33mWebSocketProvider[39m [33m=[39m ({ children }[33m:[39m [33mWebSocketProviderProps[39m) [33m=>[39m {
    [31m[1m>[22m[39m[90m 30 |[39m   [36mconst[39m { token } [33m=[39m useContext([33mAuthContext[39m)[33m![39m[33m;[39m
     [90m    |[39m           [31m[1m^[22m[39m
     [90...(truncated)
```

## Error Summary

### Backend Errors
- [gw2][36m [  1%] [0m[31mERROR[0m integration_tests/test_health.py::test_ready_endpoint_clickhouse_failure
- [gw1][36m [  3%] [0m[31mFAILED[0m integration_tests/test_generation_service.py::test_run_synthetic_data_generation_job_e2e
- [gw3][36m [  8%] [0m[31mFAILED[0m app/tests/routes/test_api_routes_21_30.py::TestAdminRoute::test_admin_user_management
- [gw0][36m [  9%] [0m[31mFAILED[0m integration_tests/test_app.py::test_read_main
- =================================== ERRORS ====================================
- [31m[1m__________ ERROR at setup of test_ready_endpoint_clickhouse_failure ___________[0m
- [31mFAILED[0m integration_tests/test_generation_service.py::[1mtest_run_synthetic_data_generation_job_e2e[0m - assert None is not None
- [31mFAILED[0m app/tests/routes/test_api_routes_21_30.py::[1mTestAdminRoute::test_admin_user_management[0m - AttributeError: <module 'app.services.user_service' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\user_service.py'> does not have the attribute 'get_all_users'
- [31mFAILED[0m integration_tests/test_app.py::[1mtest_read_main[0m
- [31mERROR[0m integration_tests/test_health.py::[1mtest_ready_endpoint_clickhouse_failure[0m
- [FAIL] TESTS FAILED with exit code 2 after 31.45s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (24.255 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
