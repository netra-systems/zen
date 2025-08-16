# Netra AI Platform - Test Report

**Generated:** 2025-08-15T21:11:42.116869  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 832  
**Passed:** 809  
**Failed:** 1  
**Skipped:** 22  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 832 | 809 | 1 | 22 | 0 | 74.21s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.40s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 74.61s
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
4 workers [2314 items]

scheduling tests via LoadScheduling

app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_job_cancellation_by_admin 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_reuse_for_same_user 
app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_clickhouse_service.py::TestClickHouseConnection::test_query_with_parameters 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_reuse_for_same_user 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_pool_management 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_pool_management 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_concurrent_agent_limit_enforcement 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_concurrent_agent_limit_enforcement 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_task_execution_tracking 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_task_execution_tracking 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_task_failure_handling 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_llm_name 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_task_failure_handling 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_concurrent_agent_orchestration 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_multiple_executions 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_concurrent_execution 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_concurrent_execution 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_without_metadata_attribute 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_without_metadata_attribute 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_inheritance_chain 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_inheritance_chain 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_complex_kwargs 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_with_complex_kwargs 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_exception_types 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_exception_types 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_async_delay 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_concurrent_agent_orchestration 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_state_transitions 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_async_delay 
app\tests\services\apex_optimizer_agent\tools\test_cost_analyzer.py::TestCos...(truncated)
```

### Frontend Output
```

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw2][36m [ 19%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseArraySyntaxFixer::test_mixed_correct_and_incorrect_syntax
- [31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::[1mTestClickHouseArraySyntaxFixer::test_mixed_correct_and_incorrect_syntax[0m - AssertionError: assert 'toFloat64OrZero(arrayElement(metrics.incorrect, 2))' in '\n            SELECT \n                toFloat64OrZero(arrayElement(metrics.correct, 1)) as correct_field,\n                arrayElement(metrics.incorrect, 2) as incorrect_field\n            FROM test_table\n        '
- [FAIL] TESTS FAILED with exit code 2 after 73.20s


---
*Generated by Netra AI Unified Test Runner v3.0*
