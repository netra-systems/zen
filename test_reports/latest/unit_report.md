# Netra AI Platform - Test Report

**Generated:** 2025-08-14T09:38:32.516446  
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
| Backend   | 101 | 90 | 4 | 7 | 0 | 33.33s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.31s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 33.64s
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
4 workers [1450 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\supply_research_scheduler\test_schedule_management.py::TestScheduleManagement::test_get_schedule_status_with_run_history 
app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\supply_research_scheduler\test_schedule_management.py::TestScheduleManagement::test_get_schedule_status_with_run_history 
app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestScheduledResearchExecution::test_execute_scheduled_research_success 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_passes_through_correct_queries 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_passes_through_correct_queries 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_handles_client_errors 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_handles_client_errors 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_tracking 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_tracking 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_can_be_disabled 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_can_be_disabled 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_with_query_parameters 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_with_query_parameters 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_concurrent_interceptor_usage 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_concurrent_interceptor_usage 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_reset 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_statistics_reset 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_get_statistics 
[gw2][36m [  0%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_get_statistics 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_end_to_end_query_processing 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_end_to_end_query_processing 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_batch_query_processing 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_batch_query_processing 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_regex_pattern_comprehensive_coverage 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_regex_pattern_comprehensive_coverage 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_performance_optimization_caching 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw1][36m [  1%] [0m[31mFAILED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestScheduledResearchExecution::test_execute_scheduled_research_success 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_performance_optimization_caching 
app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_logging_and_debugging_support 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryFixerIntegration::test_logging_and_debugging_support 
app\tests\services\test_clickhouse_service.py::TestClickHouseConnection::test_client_initialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\...(truncated)
```

### Frontend Output
```

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw2][36m [  0%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::TestTableOperations::test_ingest_batch_with_data
- [gw1][36m [  1%] [0m[31mFAILED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::TestScheduledResearchExecution::test_execute_scheduled_research_success
- [gw3][36m [  5%] [0m[31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::TestErrorHandling::test_recover_from_partial_batch_failure
- [gw0][36m [  6%] [0m[31mFAILED[0m app\tests\services\supply_research_scheduler\test_integration.py::TestIntegrationScenarios::test_full_execution_cycle Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- [31mFAILED[0m app\tests\services\synthetic_data\test_table_operations.py::[1mTestTableOperations::test_ingest_batch_with_data[0m - AssertionError: Expected 'execute' to have been called once. Called 0 times.
- [31mFAILED[0m app\tests\services\supply_research_scheduler\test_scheduled_execution.py::[1mTestScheduledResearchExecution::test_execute_scheduled_research_success[0m - AttributeError: <module 'app.services.supply_research_scheduler' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\supply_research_scheduler.py'> does not have the attribute 'SupplyResearchService'
- [31mFAILED[0m app\tests\services\test_corpus_service_comprehensive.py::[1mTestErrorHandling::test_recover_from_partial_batch_failure[0m - AttributeError: 'CorpusService' object has no attribute 'batch_index_with_recovery'
- [31mFAILED[0m app\tests\services\supply_research_scheduler\test_integration.py::[1mTestIntegrationScenarios::test_full_execution_cycle[0m - AttributeError: <module 'app.services.supply_research_scheduler' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\supply_research_scheduler.py'> does not have the attribute 'SupplyResearchService'
- [FAIL] TESTS FAILED with exit code 2 after 31.74s


---
*Generated by Netra AI Unified Test Runner v3.0*
