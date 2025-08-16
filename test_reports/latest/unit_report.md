# Netra AI Platform - Test Report

**Generated:** 2025-08-16T09:35:14.245633  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 549  
**Passed:** 528  
**Failed:** 2  
**Skipped:** 19  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 549 | 528 | 2 | 19 | 0 | 73.14s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.54s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 73.68s
- **Exit Code:** 15

### Backend Configuration
```
--category unit -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category unit
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: unit
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services
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
4 workers [2477 items]

scheduling tests via LoadScheduling

app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_clickhouse_service.py::TestWorkloadEventsOperations::test_workload_events_operations 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_concurrent_agent_execution 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_concurrent_agent_execution 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_string_input 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_string_input 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_dict_input 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_incremental 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_dict_input 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceBasic::test_run_agent_with_request_model 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceBasic::test_run_agent_with_request_model 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_service_initialization 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_service_initialization 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_execution_basic 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_execution_basic 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_with_model_dump_fallback 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_with_model_dump_fallback 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_start_agent 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_start_agent 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\test_agent_servic...(truncated)
```

### Frontend Output
```

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw2][36m [ 11%] [0m[31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::TestErrorHandling::test_database_connection_failure
- [gw3][36m [ 14%] [0m[31mFAILED[0m app\tests\services\test_circuit_breaker_integration.py::TestDatabaseClientCircuitBreaker::test_successful_db_query
- [31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::[1mTestErrorHandling::test_database_connection_failure[0m - AssertionError: Regex pattern did not match.
- [31mFAILED[0m app\tests\services\test_circuit_breaker_integration.py::[1mTestDatabaseClientCircuitBreaker::test_successful_db_query[0m - AttributeError: <module 'app.db.client' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\db\\client.py'> does not have the attribute 'async_session_factory'
- [FAIL] TESTS FAILED with exit code 2 after 71.89s
- Record was: {'elapsed': datetime.timedelta(seconds=42, microseconds=315690), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='ERROR', no=40, icon='❌'), 'line': 1028, 'message': "Task was destroyed but it is pending!\ntask: <Task pending name='Task-130' coro=<SyntheticDataService._execute_generation_workflow() running at C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\synthetic_data\\core_service.py:203> wait_for=<Future pending cb=[_chain_future.<locals>._call_check_cancel() at C:\\Users\\antho\\miniconda3\\Lib\\asyncio\\futures.py:387, Task.task_wakeup()]>>", 'module': '__init__', 'name': 'logging', 'process': (id=39752, name='MainProcess'), 'thread': (id=3288, name='MainThread'), 'time': datetime(2025, 8, 16, 9, 34, 52, 845967, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}
- Record was: {'elapsed': datetime.timedelta(seconds=42, microseconds=315690), 'exception': None, 'extra': {}, 'file': (name='__init__.py', path='C:\\Users\\antho\\miniconda3\\Lib\\logging\\__init__.py'), 'function': 'handle', 'level': (name='ERROR', no=40, icon='❌'), 'line': 1028, 'message': "Task was destroyed but it is pending!\ntask: <Task pending name='Task-134' coro=<SyntheticDataService._execute_generation_workflow() running at C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\synthetic_data\\core_service.py:203> wait_for=<Future pending cb=[_chain_future.<locals>._call_check_cancel() at C:\\Users\\antho\\miniconda3\\Lib\\asyncio\\futures.py:387, Task.task_wakeup()]>>", 'module': '__init__', 'name': 'logging', 'process': (id=39752, name='MainProcess'), 'thread': (id=3288, name='MainThread'), 'time': datetime(2025, 8, 16, 9, 34, 52, 845967, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=61200), 'Pacific Daylight Time'))}


---
*Generated by Netra AI Unified Test Runner v3.0*
