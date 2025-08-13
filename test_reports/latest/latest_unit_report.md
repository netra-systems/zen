# Netra AI Platform - Test Report

**Generated:** 2025-08-11T20:39:52.833694  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 309  
**Passed:** 107  
**Failed:** 202  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 95 | 91 | 4 | 0 | 0 | 38.22s | [FAILED] |
| Frontend  | 214 | 16 | 198 | 0 | 0 | 61.43s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 99.65s
- **Exit Code:** 2

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4
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
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
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
4 workers [1438 items]

scheduling tests via LoadScheduling

app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_agent_failure_recovery 
app\tests\services\test_generation_service_fixed.py::TestClickHouseOperationsMocked::test_save_corpus_to_clickhouse_mocked 
app\tests\services\agents\test_supervisor_service.py::test_supervisor_end_to_end 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_bulk_create 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_supervisor_service.py::test_supervisor_end_to_end 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_generation_service_fixed.py::TestClickHouseOperationsMocked::test_save_corpus_to_clickhouse_mocked 
app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_job_store_service.py::TestJobStore::test_job_store_initialization 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_job_store_initialization 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_bulk_create 
app\tests\services\test_job_store_service.py::TestJobStore::test_set_and_get_job 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_by_id 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_set_and_get_job 
app\tests\services\test_job_store_service.py::TestJobStore::test_update_job_status 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_update_job_status 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_by_id 
app\tests\services\test_job_store_service.py::TestJobStore::test_nonexistent_job 
app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_many 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_nonexistent_job 
app\tests\services\test_job_store_service.py::TestJobStore::test_global_job_store 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_job_store_service.py::TestJobStore::test_global_job_store 
app\tests\services\test_key_manager.py::test_load_from_settings_success <- ..\v2\app\tests\services\test_key_manager.py 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_key_manager.py::test_load_from_settings_success <- ..\v2\app\tests\services\test_key_manager.py 
app\tests\services\test_key_manager.py::test_load_from_settings_jwt_key_too_short <- ..\v2\app\tests\services\test_key_manager.py 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_key_manager.py::test_load_from_settings_jwt_key_too_short <- ..\v2\app\tests\services\test_key_manager.py 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_llm_cache_service.py::test_llm_cache_service_initialization 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_llm_cache_service.py::test_llm_cache_service_initialization 
app\tests\services\test_llm_cache_service.py::test_cache_set_and_get 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_llm_cache_service.py::test_cache_set_and_get 
app\tests\services\test_llm_cache_service.py::test_cache_expiration 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw2][36m [  1%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_many 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
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
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_agent_failure_recovery 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_agent_timeout_handling 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_concurrent_execution 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::...(truncated)
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

FAIL __tests__/hooks/useChatWebSocket.test.ts
  ● useChatWebSocket › should handle workflow progress update

    expect(received).toBe(expected) // Object.is equality

    Expected: 1
    Received: 0

    [0m [90m 234 |[39m     [36mconst[39m { result } [33m=[39m renderHook(() [33m=>[39m useChatWebSocket())[33m;[39m
     [90m 235 |[39m     
    [31m[1m>[22m[39m[90m 236 |[39m     expect(result[33m.[39mcurrent[33m.[39mworkflowProgress[33m.[39mcurrent_step)[33m.[39mtoBe([35m1[39m)[33m;[39m
     [90m     |[39m                                                          [31m[1m^[22m[39m
     [90m 237 |[39m     expect(result[33m.[39mcurrent[33m.[39mworkflowProgress[33m.[39mtotal_steps)[33m.[39mtoBe([35m3[39m)[33m;[39m
     [90m 238 |[39m   })[33m;[39m
     [90m 239 |[39m[0m

      at Object.toBe (__tests__/hooks/useChatWebSocket.test.ts:236:58)

  ● useChatWebSocket › should handle streaming updates

    expect(received).toBe(expected) // Object.is equality

    Expected: true
    Received: false

    [0m [90m 254 |[39m     [36mconst[39m { result } [33m=[39m renderHook(() [33m=>[39m useChatWebSocket())[33m;[39m
     [90m 255 |[39m     
    [31m[1m>[22m[39m[90m 256 |[39m     expect(result[33m.[39mcurrent[33m.[39misStreaming)[33m.[39mtoBe([36mtrue[39m)[33m;[39m
     [90m     |[39m                                        [31m[1m^[22m[39m
     [90m 257 |[39m     expect(result[33m.[39mcurrent[33m.[39mstreamingMessage)[33m.[39mtoBe([32m'Streaming content...'[39m)[33m;[39m
     [90m 258 |[39m   })[33m;[39m
     [90m 259 |[39m[0m

      at Object.toBe (__tests__/hooks/useChatWebSocket.test.ts:256:40)

  ● useChatWebSocket › should filter error messages correctly

    expect(received).toHaveLength(expected)

    Expected length: 2
    Received length: 0
    Received array:  []

    [0m [90m 308 |[39m     [36mconst[39m { result } [33m=[39m renderHook(() [33m=>[39m useChatWebSocket())[33m;[39m
     [90m 309 |[39m     
    [31m[1m>[22m[39m[90m 310 |[39m     expect(result[33m.[39mcurrent[33m.[39merrors)[33m.[39mtoHaveLength([35m2[39m)[33m;[39m
     [90m     |[39m                                   [31m[1m^[22m[39m
     [90m 311 |[39m     expect(result[33m.[39mcurrent[33m.[39merrors[[35m0[39m][33m.[39mtype)[33m.[39mtoBe([32m'error'[39m)[33m;[39m
     [90m 312 |[39m     expect(result[33m.[39mcurrent[33m.[39merrors[[35m1[39m][33m.[39mtype)[33m.[39mtoBe([32m'error'[39m)[33m;[39m
     [90m 313 |[39m   })[33m;[39m[0m

      at Object.toHaveLength (__tests__/hooks/useChatWebSocket.test.ts:310:35)

FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
  ● useKeyboardShortcuts › Hook Initialization › should register keyboard event listeners on mount

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: "keydown", Any<Function>

    Number of calls: 0

    [0m [90m 73 |[39m       })[33m;[39m
     [90m 74 |[39m       
    [31m[1m>[22m[39m[90m 75 |[39m       expect(addEventListenerSpy)[33m.[39mtoHaveBeenCalledWith([32m'keydown'[39m[33m,[39m expect[33m.[39many([33mFunction[39m))[33m;[39m
     [90m    |[39m                                   [31m[1m^[22m[39m
     [90m 76 |[39m     })[33m;[39m
     [90m 77 |[39m
     [90m 78 |[39m     it([32m'should cleanup event listeners on unmount'[39m[33m,[39m () [33m=>[39m {[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.tsx:75:35)

  ● useKeyboardShortcuts › Hook Initialization › should cleanup event listeners on unmount

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: "keydown", Any<Function>

    Number of calls: 0

    [0m [90m 82 |[39m       unmount()[33m;[39m
     [90m 83 |[39m       
    [31m[1m>[22m[39m[90m 84 |[39m       expect(removeEventListenerSpy)[33m.[39mtoHaveBeenCalledWith([32m'keydown'[39m[33m,[39m expect[33m.[39many([33mFunction[39m))[33m;[39m
     [90m    |[39m                                      [31m[1m^[22m[39m
     [90m 85 |[39m     })[33m;[39m
     [90m 86 |[39m   })[33m;[39m
     [90m 87 |[39m[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.tsx:84:38)

  ● useKeyboardShortcuts › Focus Management › should focus message input when / key is pressed

    expect(jest.fn()).toHaveBeenCalled()

    Expected number of calls: >= 1
    Received number of calls:    0

    [0m [90m  99 |[39m       })[33m;[39m
     [90m 100 |[39m
    [31m[1m>[22m[39m[90m 101 |[39m       expect(focusMock)[33m.[39mtoHaveBeenCalled()[33m;[39m
     [90m     |[39m                         [31m[1m^[22m[39m
     [90m 102 |[39m     })[33m;[39m
     [90m 103 |[39m
     [90m 104 |[39m     it([32m'should not trigger shortcuts when typing in input fields'[39m[33m,[39m () [33m=>[39m {[0m

      at Object.toHaveBeenCalled (__tests__/hooks/useKeyboardShortcuts.test.tsx:101:25)

  ● useKeyboardShortcuts › Thread Navigation › should navigate to previous thread with Alt+Left

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: "1"

    Number of calls: 0

    [0m [90m 142 |[39m       })[33m;[39m
     [90m 143 |[39m
    [31m[1m>[22m[39m[90m 144 |[39m       expect(mockThreadStore[33m.[39msetCurrentThread)[33m.[39mtoHaveBeenCalledWith([32m'1'[39m)[33m;[39m
     [90m     |[39m                                                [31m[1m^[22m[39m
     [90m 145 |[39m     })[33m;[39m
     [90m 146 |[39m
     [90m 147 |[39m     it([32m'should navigate to next thread with Alt+Right'[39m[33m,[39m () [33m=>[39m {[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.tsx:144:48)

  ● useKeyboardShortcuts › Thread Navigation › should navigate to next thread with Alt+Right

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: "3"

    Number of calls: 0

    [0m [90m 159 |[39m       })[33m;[39m
     [90m 160 |[39m
    [31m[1m>[22m[39m[90m 161 |[39m       expect(mockThreadStore[33m.[39msetCurrentThread)[33m.[39mtoHaveBeenCalledWith([32m'3'[39m)[33m;[39m
     [90m     |[39m                                                [31m[1m^[22m[39m
     [90m 162 |[39m     })[33m;[39m
     [90m 163 |[39m
     [90m 164 |[39m     it([32m'should wrap around when navigating threads'[39m[33m,[39m () [33m=>[39m {[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.tsx:161:48)

  ● useKeyboardShortcuts › Thread Navigation › should wrap around when navigating threads

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: "1"

    Number of calls: 0

    [0m [90m 178 |[39m       })[33m;[39m
     [90m 179 |[39m
    [31m[1m>[22m[39m[90m 180 |[39m       expect(mockThreadStore[33m.[39msetCurrentThread)[33m.[39mtoHaveBeenCalledWith([32m'1'[39m)[33m;[39m
     [90m     |[39m                                                [31m[1m^[22m[39m
     [90m 181 |[39m     })[33m;[39m
     [90m 182 |[39m   })[33m;[39m
     [90m 183 |[39m[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.tsx:180:48)

  ● useKeyboardShortcuts › Escape Key Handling › should handle escape key when processing

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: false

    Number of calls: 0

    [0m [90m 193 |[39m       })[33m;[39m
     [90m 194 |[39m
    [31m[1m>[22m[39m[90m 195 |[39m       expect(mockChatStore[33m.[39msetProcessing)[33m.[39mtoHaveBeenCalledWith([36mfalse[39m)[33m;[39m
     [90m     |[39m                                           [31m[1m^[22m[39m
     [90m 196 |[39m     })[33m;[39m
     [90m 197 |[39m
     [90m 198 |[39m     it([32m'should not interfere with escape in input fields'[39m[33m,[39m () [33m=>[39m {[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.tsx:195:43)

  ● useKeyboardShortcuts › Scroll Navigation › should scroll to top with Ctrl+Home

    expect(jest.fn()).toHaveBeenCalledWith(...expected)

    Expected: {"behavior": "smooth", "top": 0}

    Number of calls: 0

    [0m [90m 239 |[39m       })[33m;[39m
     [90m 240 |[39m
    [31m[1m>[22m[39m[90m 241 |[39m       expect(scrollToMock)[33m.[39mtoHaveBeenCalledWith({ top[33m:[39m [35m0[39m[33m,[39m behavior[33m:[39m [32m'smooth'[39m })[33m;[39m
     [90m     |[39m                            [31m[1m^[22m[39m
     [90m 242 |[39m     })[33m;[39m
     [90m 243 |[39m
     [90m 244 |[39m     it([32m'should scroll to bottom with Ctrl+End'[39m[33m,[39m () [33m=>[39m {[0m

      at Object.toHaveBeenCalledWith (__tests__/hooks/useKeyboardShortcuts.test.ts...(truncated)
```

## Error Summary

### Backend Errors
- [gw2][36m [  1%] [0m[31mFAILED[0m app\tests\services\test_database_repositories.py::TestBaseRepository::test_repository_get_many
- [gw1][36m [  3%] [0m[31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::TestApexOptimizerToolSelection::test_tool_selection_latency_optimization
- [gw0][36m [  6%] [0m[31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceOrchestration::test_websocket_message_handling_thread_operations
- [gw3][36m [  6%] [0m[31mFAILED[0m app\tests\services\test_llm_cache_service.py::test_cache_stats
- [31mFAILED[0m app\tests\services\test_database_repositories.py::[1mTestBaseRepository::test_repository_get_many[0m - AttributeError: 'NoneType' object has no attribute 'create'
- [31mFAILED[0m app\tests\services\test_apex_optimizer_tool_selection.py::[1mTestApexOptimizerToolSelection::test_tool_selection_latency_optimization[0m - AssertionError: assert 'cost_reduction_quality_preservation' == 'tool_latency_optimization'
- [31mFAILED[0m app\tests\services\test_agent_service_orchestration.py::[1mTestAgentServiceOrchestration::test_websocket_message_handling_thread_operations[0m - AssertionError: expected call not found.
- [31mFAILED[0m app\tests\services\test_llm_cache_service.py::[1mtest_cache_stats[0m - KeyError: 'total_hits'
- [FAIL] TESTS FAILED with exit code 2 after 37.38s

### Frontend Errors
- [FAIL] CHECKS FAILED with exit code 1
- FAIL __tests__/hooks/useChatWebSocket.test.ts
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx (5.664 s)
- FAIL __tests__/imports/internal-imports.test.tsx (5.729 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.649 s)
- FAIL __tests__/system/startup.test.tsx (12.434 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.35 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (26.524 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (55.002 s)
- FAIL __tests__/hooks/useChatWebSocket.test.ts
- FAIL __tests__/hooks/useKeyboardShortcuts.test.tsx
- FAIL __tests__/hooks/useAgent.test.tsx
- FAIL __tests__/components/UIComponents.test.tsx
- FAIL __tests__/components/ThinkingIndicator.test.tsx
- FAIL __tests__/hooks/additionalHooks.test.tsx
- FAIL __tests__/services/webSocketService.test.ts
- FAIL __tests__/components/ChatHistory.test.tsx
- FAIL __tests__/hooks/useWebSocketLifecycle.test.tsx
- FAIL __tests__/integration/critical-integration.test.tsx
- FAIL __tests__/components/ChatSidebar.test.tsx
- FAIL __tests__/components/FinalReportView.test.tsx
- FAIL __tests__/auth/service.test.ts
- FAIL __tests__/unified-chat-v5.test.tsx
- FAIL __tests__/components/ChatComponents.test.tsx
- FAIL __tests__/components/AgentStatusPanel.test.tsx
- FAIL __tests__/chat/chatUIUXComprehensive.test.tsx
- FAIL __tests__/auth/context.test.tsx
- FAIL __tests__/integration/advanced-integration.test.tsx
- FAIL __tests__/imports/external-imports.test.tsx (5.664 s)
- FAIL __tests__/imports/internal-imports.test.tsx (5.729 s)
- FAIL __tests__/components/ChatHistorySection.test.tsx (10.649 s)
- FAIL __tests__/system/startup.test.tsx (12.434 s)
- FAIL __tests__/components/chat/MainChat.test.tsx (13.35 s)
- FAIL __tests__/chat/chatUIUXCore.test.tsx
- FAIL __tests__/chat/ui-improvements.test.tsx
- FAIL __tests__/integration/comprehensive-integration.test.tsx (26.524 s)
- FAIL __tests__/components/chat/MessageInput.test.tsx (55.002 s)


---
*Generated by Netra AI Unified Test Runner v3.0*
