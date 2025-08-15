# Netra AI Platform - Test Report

**Generated:** 2025-08-15T10:41:02.434065  
**Test Level:** agents - Agent-specific unit tests (2-3 minutes)  
**Purpose:** Quick validation of agent functionality during development

## Test Summary

**Total Tests:** 56  
**Passed:** 54  
**Failed:** 0  
**Skipped:** 2  
**Errors:** 0  
**Overall Status:** [PASSED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 56 | 54 | 0 | 2 | 0 | 17.43s | [PASSED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** agents
- **Description:** Agent-specific unit tests (2-3 minutes)
- **Purpose:** Quick validation of agent functionality during development
- **Timeout:** 180s
- **Coverage Enabled:** No
- **Total Duration:** 17.43s
- **Exit Code:** 0

### Backend Configuration
```
app/tests/agents/test_data_sub_agent.py tests/test_actions_sub_agent.py -v --fail-fast --parallel=4
```

### Frontend Configuration
```

```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: all
  Parallel: 4
  Coverage: disabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/agents/test_data_sub_agent.py tests/test_actions_sub_agent.py -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
created: 4/4 workers
4 workers [56 items]

scheduling tests via LoadScheduling

app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_defaults 
app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_text_data 
app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_success 
app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_required_fields 
[gw2][36m [  1%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_defaults 
app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_custom_config 
[gw2][36m [  3%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_custom_config 
[gw1][36m [  5%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_required_fields 
app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_missing_fields 
app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_redis 
[gw1][36m [  7%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_missing_fields 
[gw3][36m [  8%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_text_data 
[gw2][36m [ 10%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_redis 
app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_data_types 
app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_metadata 
[gw1][36m [ 12%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_data_types 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_retry_on_failure 
[gw0][36m [ 14%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_success 
app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_validation_failure 
app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_json_data 
[gw2][36m [ 16%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_metadata 
[gw0][36m [ 17%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_validation_failure 
app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_external_source 
[gw3][36m [ 19%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_json_data 
app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_batch_processing 
[gw2][36m [ 21%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_external_source 
app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_with_pipeline 
[gw0][36m [ 23%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_batch_processing 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_redis_connection_failure_recovery <- app\tests\helpers\shared_test_types.py 
[gw2][36m [ 25%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_redis_connection_failure_recovery <- app\tests\helpers\shared_test_types.py 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_database_connection_failure 
app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_expiration 
[gw3][36m [ 26%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_with_pipeline 
[gw2][36m [ 28%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_database_connection_failure 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_supervisor 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_async_operations <- app\tests\helpers\shared_test_types.py 
[gw0][36m [ 30%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_expiration 
[gw2][36m [ 32%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_supervisor 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_service_initialization <- app\tests\helpers\shared_test_types.py 
[gw3][36m [ 33%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_async_operations <- app\tests\helpers\shared_test_types.py 
[gw0][36m [ 35%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_service_initialization <- app\tests\helpers\shared_test_types.py 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_websocket 
app/tests/agents/test_data_sub_agent.py::TestPerformance::test_concurrent_processing 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_basic_operations <- app\tests\helpers\shared_test_types.py 
[gw0][36m [ 37%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_basic_operations <- app\tests\helpers\shared_test_types.py 
app/tests/agents/test_data_sub_agent.py::TestStateManagement::test_state_recovery 
[gw3][36m [ 39%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_websocket 
[gw0][36m [ 41%] [0m[33mSKIPPED[0m app/tests/agents/test_data_sub_agent.py::TestStateManagement::test_state_recovery 
[gw2][36m [ 42%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestPerformance::test_concurrent_processing 
tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_agent_initialization_success 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_database 
app/tests/agents/test_data_sub_agent.py::TestPerformance::test_memory_efficiency 
[gw0][36m [ 44%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_agent_initialization_success 
[gw3][36m [ 46%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_database 
tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_reliability_wrapper_initialized 
[gw2][36m [ 48%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestPerformance::test_memory_efficiency 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_valid_prerequisites 
app/tests/agents/test_data_sub_agent.py::TestStateManagement::test_state_persistence 
[gw0][36m [ 50%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_reliability_wrapper_initialized 
[gw2][36m [ 51%] [0m[33mSKIPPED[0m app/tests/agents/test_data_sub_agent.py::TestStateManagement::test_state_persistence 
tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_fallback_strategy_initialized 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_data_result 
[gw0][36m [ 53%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_fallback_strategy_initialized 
[gw3][36m [ 55%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_valid_prerequisites 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_both_missing 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_optimizations 
[gw2][36m [ 57%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_data_result 
tests/test_actions_sub_agent.py::TestSuccessfulExecution::test_execute_success_with_valid_json 
[gw0][36m [ 58%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_both_missing 
[gw3][36m [ 60%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_optimizations 
tests/test_actions_sub_agent.py::TestSuccessfulExecution::test_execute_without_stream_updates 
tests/test_actions_sub_agent.py::TestJSONExtractionAndFal...(truncated)
```

### Frontend Output
```

```
---
*Generated by Netra AI Unified Test Runner v3.0*
