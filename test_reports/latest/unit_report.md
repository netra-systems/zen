# Netra AI Platform - Test Report

**Generated:** 2025-08-17T19:13:48.731805  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 322  
**Passed:** 308  
**Failed:** 4  
**Skipped:** 10  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 322 | 308 | 4 | 10 | 0 | 51.57s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.16s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 51.73s
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
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services -p test_framework.pytest_bad_test_plugin --test-component backend
================================================================================
[BAD TEST DETECTOR] Initialized for backend tests
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [2484 items]

scheduling tests via LoadScheduling

app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
app\tests\services\test_corpus_audit.py::TestCorpusAuditRepository::test_search_records_with_filters 
[gw0][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
[gw0][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
[gw0][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_concurrent_agent_execution 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_concurrent_agent_execution 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_string_input 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_string_input 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_dict_input 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_dict_input 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceBasic::test_run_agent_with_request_model 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceBasic::test_run_agent_with_request_model 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_service_initialization 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_service_initialization 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_execution_basic 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_execution_basic 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_with_model_dump_fallback 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_agent_run_with_model_dump_fallback 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_start_agent 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_incremental 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_start_agent 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_user_message 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_user_message 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_thread_operations 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_thread_operations 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_stop_agent 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_core.py::TestAgentServiceOrchestrationCore::test_websocket_message_handling_stop_agent 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_me...(truncated)
```

### Frontend Output
```

usage: test_frontend.py [-h]
                        [--category {unit,integration,components,hooks,store,websocket,auth,e2e,smoke}]
                        [--keyword KEYWORD] [--e2e] [--cypress-open] [--watch]
                        [--coverage] [--update-snapshots] [--lint] [--fix]
                        [--type-check] [--build] [--check-deps]
                        [--install-deps] [--verbose] [--isolation]
                        [--cleanup-on-exit]
                        [tests ...]
test_frontend.py: error: unrecognized arguments: --no-cov -x --maxfail=1

```

## Error Summary

### Backend Errors
- [gw0][36m [  8%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_error_recovery.py::TestErrorRecovery::test_memory_overflow_handling
- [gw1][36m [ 12%] [0m[31mFAILED[0m app\tests\services\synthetic_data\test_admin_visibility.py::TestAdminVisibility::test_job_cancellation_by_admin
- [gw2][36m [ 12%] [0m[31mFAILED[0m app\tests\services\test_circuit_breaker_integration.py::TestDatabaseClientCircuitBreaker::test_db_circuit_breaker_fallback
- [gw3][36m [ 12%] [0m[31mFAILED[0m app\tests\services\test_database_transaction_performance.py::TestTransactionPerformanceAndScaling::test_deadlock_recovery_performance Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- 2025-08-17 19:13:41.261 | ERROR    | logging:handle:1028 | Task was destroyed but it is pending!
- [31mFAILED[0m app\tests\services\synthetic_data\test_error_recovery.py::[1mTestErrorRecovery::test_memory_overflow_handling[0m - AttributeError: 'SyntheticDataService' object has no attribute 'generate_with_memory_limit'
- [31mFAILED[0m app\tests\services\synthetic_data\test_admin_visibility.py::[1mTestAdminVisibility::test_job_cancellation_by_admin[0m - assert False == True
- [31mFAILED[0m app\tests\services\test_circuit_breaker_integration.py::[1mTestDatabaseClientCircuitBreaker::test_db_circuit_breaker_fallback[0m - assert 0 == 1
- [31mFAILED[0m app\tests\services\test_database_transaction_performance.py::[1mTestTransactionPerformanceAndScaling::test_deadlock_recovery_performance[0m - assert False
- [FAIL] TESTS FAILED with exit code 2 after 50.50s


---
*Generated by Netra AI Unified Test Runner v3.0*
