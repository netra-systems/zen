# Netra AI Platform - Test Report

**Generated:** 2025-08-12T12:48:32.489118  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 469  
**Passed:** 189  
**Failed:** 280  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 174 | 171 | 3 | 0 | 0 | 45.83s | [FAILED] |
| Frontend  | 295 | 18 | 277 | 0 | 0 | 93.87s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 139.69s
- **Exit Code:** 2

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 -m not real_services
```

### Frontend Configuration
```
--category unit
```

## Test Output

### Backend Output
```
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: development

Running command:
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [1439 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_supervisor_service.py::test_supervisor_end_to_end 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_agent_failure_recovery 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_bulk_create 
app\tests\services\test_generation_service_fixed.py::TestClickHouseOperationsMocked::test_get_corpus_from_clickhouse_mocked 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_generation_service_fixed.py::TestClickHouseOperationsMocked::test_get_corpus_from_clickhouse_mocked 
app\tests\services\test_generation_service_fixed.py::TestClickHouseOperationsMocked::test_save_corpus_to_clickhouse_mocked 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_bulk_create 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_by_id 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_generation_service_fixed.py::TestClickHouseOperationsMocked::test_save_corpus_to_clickhouse_mocked 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_supervisor_service.py::test_supervisor_end_to_end 
app\tests\services\test_job_store_service.py::TestJobStore::test_job_store_initialization 
app\tests\services\agents\test_tools.py::test_tool_dispatcher 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_job_store_initialization 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_by_id 
app\tests\services\test_job_store_service.py::TestJobStore::test_set_and_get_job 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_many 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_set_and_get_job 
app\tests\services\test_job_store_service.py::TestJobStore::test_update_job_status 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_update_job_status 
app\tests\services\test_job_store_service.py::TestJobStore::test_nonexistent_job 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_many 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_update 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_nonexistent_job 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_job_store_service.py::TestJobStore::test_global_job_store 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_update 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_delete 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_global_job_store 
app\tests\services\test_key_manager.py::test_load_from_settings_success 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_key_manager.py::test_load_from_settings_success 
app\tests\services\test_key_manager.py::test_load_from_settings_jwt_key_too_short 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_key_manager.py::test_load_from_settings_jwt_key_too_short 
app\tests\services\test_llm_cache_service.py::test_llm_cache_service_initialization 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_llm_cache_service.py::test_llm_cache_service_initialization 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_llm_cache_service.py::test_cache_set_and_get 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_llm_cache_service.py::test_cache_set_and_get 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\test_llm_cache_service.py::test_cache_expiration 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw3][36m [  1%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_delete 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\services\t...(truncated)
```

### Frontend Output
```

> netra-frontend-apex-v1@0.1.0 test
> jest __tests__/unit components/**/*.test.tsx hooks/**/*.test.ts

  Invalid testPattern __tests__/unit|components/**/*.test.tsx|hooks/**/*.test.ts supplied. Running all tests instead.
  Invalid testPattern __tests__/unit|components/**/*.test.tsx|hooks/**/*.test.ts supplied. Running all tests instead.
================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- __tests__/unit components/**/*.test.tsx hooks/**/*.test.ts
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 1
================================================================================

FAIL __tests__/hooks/additionalHooks.test.tsx (8.936 s)
  ● test_useDemoWebSocket_connection › should establish demo WebSocket connection

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
      at renderHook (node_modules/@testing-library/react/dist/pure.js:340:7)
      at Object.<anonymous> (__tests__/hooks/additionalHooks.test.tsx:29:34)

  ● test_useDemoWebSocket_connection › should handle message queuing when disconnected

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
      at renderHook (node_modules/@testing-library/react/dist/pure.js:340:7)
      at Object.<anonymous> (__tests__/hooks/additionalHooks.test.tsx:47:34)

  ● test_useDemoWebSocket_connection › should handle reconnection on disconnect

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
      at renderHook (node_modules/@testing-library/react/dist/pure.js:340:7)
      at Object.<anonymous> (__tests__/hooks/additionalHooks.test.tsx:77:34)

  ● test_useMediaQuery_responsive › should handle debouncing for rapid changes

    expect(received).toBe(expected) // Object.is equality

    Expected: false
    Received: true

    [0m [90m 170 |[39m     
     [90m 171 |[39m     [90m// Should not update immediately[39m
    [31m[1m>[22m[39m[90m 172 |[39m     expect(result[33m.[39mcurrent)[33m.[39mtoBe([36mfalse[39m)[33m;[39m
     [90m     |[39m                            [31m[1m^[22m[39m
     [90m 173 |[39m     
     [90m 174 |[39m     [90m// Wait for debounce[39m
     [90m 175 |[39m     [36mawait[39m waitFor(() [33m=>[39m {[0m

      at Object.toBe (__tests__/hooks/additionalHooks.test.tsx:172:28)

FAIL __tests__/hooks/useAgent.test.tsx (9.002 s)
  ● Console

    console.error
      An update to WebSocketProvider inside a test was not wrapped in act(...).
      
      When testing, code that causes React state updates should be wrapped into act(...):
      
      act(() => {
        /* fire events that update state */
      });
      /* assert on the output */
      
      This ensures that you're testing the behavior the user would see in the browser. Learn more at https://react.dev/link/wrap-tests-with-act

    [0m [90m 120 |[39m       [36mreturn[39m[33m;[39m
     [90m 121 |[39m     }
    [31m[...(truncated)
```

## Error Summary

### Backend Errors
- [gw3][36m [  1%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_delete
- [gw1][36m [  3%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_multi_objective
- [gw2][36m [ 12%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_service.py::TestQualityGateService::test_validate_with_strict_mode
- [31mFAILED[0m app\tests\services\test_database_repositories.py::[1mTestBaseRepository::test_repository_delete[0m - AssertionError: assert <AsyncMock id='2318685378016'> is None
- [31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::[1mTestApexOptimizerToolSelection::test_tool_selection_multi_objective[0m - pydantic_core._pydantic_core.ValidationError: 2 validation errors for RequestModel
- [31mFAILED[0m app\tests\services\test_quality_gate_service.py::[1mTestQualityGateService::test_validate_with_strict_mode[0m - AssertionError: assert True == False
- [FAIL] TESTS FAILED with exit code 2 after 44.14s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/hooks/additionalHooks.test.tsx (8.936 s)
- FAIL __tests__/hooks/useAgent.test.tsx (9.002 s)
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx (11.194 s)
- FAIL __tests__/integration/critical-integration.test.tsx (11.698 s)
- FAIL __tests__/auth/context.test.tsx (12.086 s)
- FAIL __tests__/components/AgentStatusPanel.test.tsx (12.93 s)
- FAIL __tests__/components/ChatHistory.test.tsx (13.126 s)
- FAIL __tests__/integration/advanced-integration.test.tsx (13.508 s)
- FAIL __tests__/setup/websocket-mock.ts
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/utils/test-utils.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx (18.498 s)
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/system/startup.test.tsx (19.559 s)
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (24.467 s)
- FAIL __tests__/imports/internal-imports.test.tsx (24.813 s)
- FAIL __tests__/imports/external-imports.test.tsx (26.443 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/components/ChatHistorySection.test.tsx (32.377 s)
- FAIL __tests__/integration/comprehensive-integration.test.tsx (35.062 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (45.505 s)
- FAIL __tests__/components/ChatComponents.test.tsx (85.057 s)
- FAIL __tests__/hooks/additionalHooks.test.tsx (8.936 s)
- FAIL __tests__/hooks/useAgent.test.tsx (9.002 s)
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx (11.194 s)
- FAIL __tests__/integration/critical-integration.test.tsx (11.698 s)
- FAIL __tests__/auth/context.test.tsx (12.086 s)
- FAIL __tests__/components/AgentStatusPanel.test.tsx (12.93 s)
- FAIL __tests__/components/ChatHistory.test.tsx (13.126 s)
- FAIL __tests__/integration/advanced-integration.test.tsx (13.508 s)
- FAIL __tests__/setup/websocket-mock.ts
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/utils/test-utils.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx (18.498 s)
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/system/startup.test.tsx (19.559 s)
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/components/chat/MainChat.test.tsx (24.467 s)
- FAIL __tests__/imports/internal-imports.test.tsx (24.813 s)
- FAIL __tests__/imports/external-imports.test.tsx (26.443 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/components/ChatHistorySection.test.tsx (32.377 s)
- FAIL __tests__/integration/comprehensive-integration.test.tsx (35.062 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (45.505 s)
- FAIL __tests__/components/ChatComponents.test.tsx (85.057 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
