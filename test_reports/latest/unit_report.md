# Netra AI Platform - Test Report

**Generated:** 2025-08-14T09:21:17.625292  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 101  
**Passed:** 90  
**Failed:** 4  
**Skipped:** 7  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 101 | 90 | 4 | 7 | 0 | 29.92s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 29.92s
- **Exit Code:** 2

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
4 workers [1450 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\supply_research_scheduler\test_schedule_management.py::TestScheduleManagement::test_get_schedule_status_with_run_history 
app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_schedule_management.py::TestScheduleManagement::test_get_schedule_status_with_run_history 
app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestScheduledResearchExecution::test_execute_scheduled_research_success 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_passes_through_correct_queries 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_passes_through_correct_queries 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_handles_client_errors 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_handles_client_errors 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_tracking 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_tracking 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_can_be_disabled 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_can_be_disabled 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_with_query_parameters 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_with_query_parameters 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_concurrent_interceptor_usage 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_concurrent_interceptor_usage 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_reset 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_reset 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_get_statistics 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_get_statistics 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_end_to_end_query_processing 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_end_to_end_query_processing 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_batch_query_processing 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_batch_query_processing 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_regex_pattern_comprehensive_coverage 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_regex_pattern_comprehensive_coverage 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_performance_optimization_caching 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
[gw3][36m [  2%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_m...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- [gw3][36m [  2%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data
- [gw1][36m [  2%] [0m[31mFAILED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestScheduledResearchExecution::test_execute_scheduled_research_success
- [gw2][36m [  6%] [0m[31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::TestErrorHandling::test_recover_from_partial_batch_failure
- [gw0][36m [  6%] [0m[31mFAILED[0m app\tests\services\supply_research_scheduler\test_integration.py::TestIntegrationScenarios::test_full_execution_cycle Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- [31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::[1mTestTableOperations::test_ingest_batch_with_data[0m - AssertionError: Expected 'execute' to have been called once. Called 0 times.
- [31mFAILED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::[1mTestScheduledResearchExecution::test_execute_scheduled_research_success[0m - AttributeError: <module 'app.services.supply_research_scheduler' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\supply_research_scheduler.py'> does not have the attribute 'SupplyResearchService'
- [31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::[1mTestErrorHandling::test_recover_from_partial_batch_failure[0m - AttributeError: 'CorpusService' object has no attribute 'batch_index_with_recovery'
- [31mFAILED[0m app\tests\services\supply_research_scheduler\test_integration.py::[1mTestIntegrationScenarios::test_full_execution_cycle[0m - AttributeError: <module 'app.services.supply_research_scheduler' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\supply_research_scheduler.py'> does not have the attribute 'SupplyResearchService'
- [FAIL] TESTS FAILED with exit code 2 after 29.07s


---
*Generated by Netra AI Unified Test Runner v3.0*
