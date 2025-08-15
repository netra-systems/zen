# Netra AI Platform - Test Report

**Generated:** 2025-08-15T10:39:59.405438  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 776  
**Passed:** 753  
**Failed:** 2  
**Skipped:** 21  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 776 | 753 | 2 | 21 | 0 | 72.63s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.76s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 73.39s
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
4 workers [2260 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_agent_resource_cleanup_on_error 
app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_metrics_export_json 
app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_audit_log_generation 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_metrics_export_json 
app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_time_series_data_retrieval 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_time_series_data_retrieval 
app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_comprehensive_report_generation 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_agent_resource_cleanup_on_error 
app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_comprehensive_report_generation 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_collector_status 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_collector_status 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_monitoring_lifecycle 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestCorpusMetricsCollector::test_monitoring_lifecycle 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\test_corpus_metrics.py::TestCoreMetricsCollector::test_operation_timing 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentErrorRecovery::test_circuit_breaker_pattern 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestCoreMetricsCollector::test_operation_timing 
app\tests\services\test_agent_service_orchestration.py::TestAgentServiceBasic::test_run_agent_with_request_model 
app\tests\services\test_corpus_metrics.py::TestQualityMetricsCollector::test_quality_trend_tracking 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration.py::TestAgentServiceBasic::test_run_agent_with_request_model 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestQualityMetricsCollector::test_quality_trend_tracking 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_service_initialization 
app\tests\services\test_corpus_metrics.py::TestMetricsExporter::test_json_export 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_service_initialization 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestMetricsExporter::test_json_export 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
app\tests\services\test_corpus_metrics.py::TestMetricsExporter::test_prometheus_export 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_corpus_metrics.py::TestMetricsExporter::test_prometheus_export 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_validation_missing_required 
app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_status_enum 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_dict_conversion 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_status_enum 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_json_serialization 
app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_schema 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_edge_cases 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_schema 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_instantiation 
app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_create_schema 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_get_metadata 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestBaseTool::test_base_tool_execute_wrapper 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_create_schema 
app\tests\services\test_corpus_service.py::TestCorpusService::test_corpus_service_import 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handl...(truncated)
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
- [gw3][36m [ 16%] [0m[31mFAILED[0m app\tests\services\test_permission_service_core.py::TestDetectDeveloperStatus::test_detect_developer_with_dev_mode_env
- [gw2][36m [ 19%] [0m[31mFAILED[0m app\tests\services\test_quality_gate_metrics.py::TestQualityGateMetrics::test_calculate_relevance_with_context
- [31mFAILED[0m app\tests\services\test_permission_service_core.py::[1mTestDetectDeveloperStatus::test_detect_developer_with_dev_mode_env[0m - assert True == False
- [31mFAILED[0m app\tests\services\test_quality_gate_metrics.py::[1mTestQualityGateMetrics::test_calculate_relevance_with_context[0m - AssertionError
- [FAIL] TESTS FAILED with exit code 2 after 71.74s


---
*Generated by Netra AI Unified Test Runner v3.0*
