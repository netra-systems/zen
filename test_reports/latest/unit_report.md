# Netra AI Platform - Test Report

**Generated:** 2025-08-15T14:51:10.468461  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 949  
**Passed:** 927  
**Failed:** 3  
**Skipped:** 19  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 949 | 927 | 3 | 19 | 0 | 55.06s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.28s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 55.34s
- **Exit Code:** 255

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
4 workers [2287 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_performance_profiling 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_with_duration 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_performance_profiling 
app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_alert_configuration 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_graceful_degradation_under_load <- tests\services\test_agent_service_orchestration_workflows.py 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_graceful_degradation_under_load <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_error_propagation_and_isolation <- tests\services\test_agent_service_orchestration_workflows.py 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_with_duration 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_failure 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_failure 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_success 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_success 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_failure 
app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_measures_duration 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_measures_duration 
app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_without_context 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_without_context 
app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_create_audit_logger_factory 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_create_audit_logger_factory 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_end_to_end_audit_workflow 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_end_to_end_audit_workflow 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_large_result_data_handling 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_large_result_data_handling 
app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_metadata_edge_cases 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_error_propagation_and_isolation <- tests\services\test_agent_service_orchestration_workflows.py 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_creation_and_assignment 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_concrete_tool_run_method 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_creation_and_assignment 
app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_collector_initialization 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_reuse_for_same_user 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\servic...(truncated)
```

### Frontend Output
```
================================================================================
NETRA AI PLATFORM - FRONTEND TEST RUNNER
================================================================================

================================================================================
Running Jest Tests
--------------------------------------------------------------------------------
Running: npm run test -- --forceExit --detectOpenHandles --testMatch **/__tests__/@(components|hooks|store|services|lib|utils)/**/*.test.[jt]s?(x)
--------------------------------------------------------------------------------

================================================================================
[FAIL] CHECKS FAILED with exit code 255
================================================================================

Cleaning up test processes...

'hooks' is not recognized as an internal or external command,
operable program or batch file.

```

## Error Summary

### Backend Errors
- [gw2][36m [ 29%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::TestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query
- [gw0][36m [ 37%] [0m[31mFAILED[0m app\tests\services\test_state_persistence.py::TestStatePersistence::test_save_agent_state
- [gw3][36m [ 41%] [0m[31mFAILED[0m app\tests\services\test_schema_validation_service.py::TestSchemaValidationService::test_agent_message_schema Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- [31mFAILED[0m app\tests\services\test_clickhouse_query_fixer.py::[1mTestClickHouseQueryInterceptor::test_interceptor_fixes_and_executes_query[0m - assert 2 == 1
- [31mFAILED[0m app\tests\services\test_state_persistence.py::[1mTestStatePersistence::test_save_agent_state[0m - TypeError: StatePersistenceService.__init__() takes 1 positional argument but 2 were given
- [31mFAILED[0m app\tests\services\test_schema_validation_service.py::[1mTestSchemaValidationService::test_agent_message_schema[0m - pydantic_core._pydantic_core.ValidationError: 4 validation errors for AgentUpdatePayload
- [FAIL] TESTS FAILED with exit code 2 after 54.00s


---
*Generated by Netra AI Unified Test Runner v3.0*
