# Netra AI Platform - Test Report

**Generated:** 2025-08-15T11:45:09.639333  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 759  
**Passed:** 745  
**Failed:** 1  
**Skipped:** 12  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 759 | 745 | 1 | 12 | 1 | 81.86s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.33s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 82.18s
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

app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_performance_profiling 
app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_with_duration 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_performance_profiling 
app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_alert_configuration 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_graceful_degradation_under_load <- tests\services\test_agent_service_orchestration_workflows.py 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_graceful_degradation_under_load <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_error_propagation_and_isolation <- tests\services\test_agent_service_orchestration_workflows.py 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_with_duration 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_failure 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_log_operation_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_success 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_success 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestCorpusAuditLogger::test_search_audit_logs_failure 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_measures_duration 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_measures_duration 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_without_context 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_error_propagation_and_isolation <- tests\services\test_agent_service_orchestration_workflows.py 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditTimer::test_timer_without_context 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_create_audit_logger_factory 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_creation_and_assignment 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_create_audit_logger_factory 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_creation_and_assignment 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_end_to_end_audit_workflow 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_reuse_for_same_user 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_reuse_for_same_user 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditIntegration::test_end_to_end_audit_workflow 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_pool_management 
app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_large_result_data_handling 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_agent_pool_management 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_failure 
app\tests\services\test_agent_service_orchestration_agents.py::TestAgentLifecycleManagement::test_concurrent_agent_limit_enforcement 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_audit.py::TestAuditPerformance::test_large_result_data_handling 
app\tests\services\test_corpus_audit.py::Tes...(truncated)
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
- [gw2][36m [ 12%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_data_quality_validation.py::TestDataQualityValidation::test_anomaly_detection_in_generated_data
- [gw3][36m [ 26%] [0m[31mERROR[0m app\tests\services\test_quality_gate_validation.py::TestErrorHandling::test_database_connection_failure <- tests\helpers\shared_test_types.py
- =================================== ERRORS ====================================
- [31m[1m____ ERROR at setup of TestErrorHandling.test_database_connection_failure _____[0m
- 2025-08-15 11:44:41.397 | ERROR    | logging:handle:1028 | Task was destroyed but it is pending!
- [31m[1mERROR   [0m asyncio:base_events.py:1821 Task was destroyed but it is pending!
- [31mFAILED[0m app\tests\services\synthetic_data\test_data_quality_validation.py::[1mTestDataQualityValidation::test_anomaly_detection_in_generated_data[0m - assert 0.066 <= 0.065
- [31mERROR[0m app\tests\services\test_quality_gate_validation.py::[1mTestErrorHandling::test_database_connection_failure[0m
- [FAIL] TESTS FAILED with exit code 2 after 80.39s


---
*Generated by Netra AI Unified Test Runner v3.0*
