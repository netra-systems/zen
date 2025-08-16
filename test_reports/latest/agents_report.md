# Netra AI Platform - Test Report

**Generated:** 2025-08-16T07:30:40.821277  
**Test Level:** agents - Agent-specific unit tests (2-3 minutes)  
**Purpose:** Quick validation of agent functionality during development

## Test Summary

**Total Tests:** 33  
**Passed:** 28  
**Failed:** 4  
**Skipped:** 1  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 33 | 28 | 4 | 1 | 0 | 15.24s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** agents
- **Description:** Agent-specific unit tests (2-3 minutes)
- **Purpose:** Quick validation of agent functionality during development
- **Timeout:** 180s
- **Coverage Enabled:** No
- **Total Duration:** 15.24s
- **Exit Code:** 2

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

app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_text_data 
app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_success 
app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_defaults 
app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_required_fields 
[gw2][36m [  1%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_required_fields 
[gw0][36m [  3%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_defaults 
app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_missing_fields 
app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_custom_config 
[gw2][36m [  5%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_missing_fields 
[gw0][36m [  7%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_custom_config 
[gw3][36m [  8%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_text_data 
app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_redis 
app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_data_types 
app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_json_data 
[gw0][36m [ 10%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataSubAgentInitialization::test_initialization_with_redis 
[gw2][36m [ 12%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataValidation::test_validate_data_types 
app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_metadata 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_retry_on_failure 
[gw3][36m [ 14%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_json_data 
app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_with_pipeline 
[gw0][36m [ 16%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_metadata 
app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_external_source 
[gw3][36m [ 17%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataTransformation::test_transform_with_pipeline 
app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_expiration 
[gw0][36m [ 19%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataEnrichment::test_enrich_with_external_source 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_redis_connection_failure_recovery <- app\tests\helpers\shared_test_types.py 
[gw0][36m [ 21%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_redis_connection_failure_recovery <- app\tests\helpers\shared_test_types.py 
[gw1][36m [ 23%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_success 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_database_connection_failure 
app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_validation_failure 
[gw0][36m [ 25%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_database_connection_failure 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_async_operations <- app\tests\helpers\shared_test_types.py 
[gw1][36m [ 26%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_process_data_validation_failure 
[gw0][36m [ 28%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_async_operations <- app\tests\helpers\shared_test_types.py 
app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_batch_processing 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_websocket 
[gw0][36m [ 30%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_websocket 
app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_database 
[gw2][36m [ 32%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_retry_on_failure 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_max_retries_exceeded 
[gw2][36m [ 33%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_max_retries_exceeded 
app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_graceful_degradation 
[gw2][36m [ 35%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestErrorHandling::test_graceful_degradation 
app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_hit 
[gw2][36m [ 37%] [0m[32mPASSED[0m app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_hit 
app/tests/agents/test_data_sub_agent.py::TestStateManagement::test_state_recovery 
[gw2][36m [ 39%] [0m[33mSKIPPED[0m app/tests/agents/test_data_sub_agent.py::TestStateManagement::test_state_recovery 
tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_agent_initialization_success 
[gw2][36m [ 41%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_agent_initialization_success 
tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_reliability_wrapper_initialized 
[gw2][36m [ 42%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_reliability_wrapper_initialized 
tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_fallback_strategy_initialized 
[gw2][36m [ 44%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestActionsSubAgentInitialization::test_fallback_strategy_initialized 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_valid_prerequisites 
[gw2][36m [ 46%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_valid_prerequisites 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_optimizations 
[gw2][36m [ 48%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_optimizations 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_data_result 
[gw2][36m [ 50%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_missing_data_result 
tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_both_missing 
[gw2][36m [ 51%] [0m[32mPASSED[0m tests/test_actions_sub_agent.py::TestEntryConditions::test_check_entry_conditions_both_missing 
tests/test_actions_sub_agent.py::TestSuccessfulExecution::test_execute_success_with_valid_json 
[gw3][36m [ 53%] [0m[31mFAILED[0m app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_expiration 
[gw1][36m [ 55%] [0m[31mFAILED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_batch_processing 
[gw0][36m [ 57%] [0m[31mFAILED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_database 
[gw2][36m [ 58%] [0m[31mFAILED[0m tests/test_actions_sub_agent.py::TestSuccessfulExecution::test_execute_success_with_valid_json Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
Loaded .env.development file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development
Loaded .env.development.local file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.development.local


================================== FAILURES ===================================
[31m[1m______________________ TestCaching.test_cache_expiration ______________________[0m
[gw3] win32 -- Python 3.12.4 C:\Users\antho\miniconda3\python.exe
[1m[31mapp\tests\agents\test_data_sub_agent.py[0m:423: in test_cache_expiration
    [0m[94massert[39;49;00m result1 != result2[90m[39;49;00m
[1m...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- [gw3][36m [ 53%] [0m[31mFAILED[0m app/tests/agents/test_data_sub_agent.py::TestCaching::test_cache_expiration
- [gw1][36m [ 55%] [0m[31mFAILED[0m app/tests/agents/test_data_sub_agent.py::TestDataProcessing::test_batch_processing
- [gw0][36m [ 57%] [0m[31mFAILED[0m app/tests/agents/test_data_sub_agent.py::TestIntegration::test_integration_with_database
- [gw2][36m [ 58%] [0m[31mFAILED[0m tests/test_actions_sub_agent.py::TestSuccessfulExecution::test_execute_success_with_valid_json Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- [31mFAILED[0m app/tests/agents/test_data_sub_agent.py::[1mTestCaching::test_cache_expiration[0m - AssertionError: assert {'status': 'processed', 'data': {'id': 'expire_test', 'content': 'data'}} != {'status': 'processed', 'data': {'id': 'expire_test', 'content': 'data'}}
- [31mFAILED[0m app/tests/agents/test_data_sub_agent.py::[1mTestDataProcessing::test_batch_processing[0m - AssertionError: assert 0 == 3
- [31mFAILED[0m app/tests/agents/test_data_sub_agent.py::[1mTestIntegration::test_integration_with_database[0m - AssertionError: assert 'DataSubAgent_1755354635' == 'saved_123'
- [31mFAILED[0m tests/test_actions_sub_agent.py::[1mTestSuccessfulExecution::test_execute_success_with_valid_json[0m - AssertionError: assert ActionPlanResult(plan_steps=[], priority='medium', estimated_duration=None, required_resources=[], success_metrics=[], metadata=AgentMetadata(created_at=datetime.datetime(2025, 8, 16, 14, 30, 36, 103834, tzinfo=datetime.timezone.utc), last_updated=datetime.datetime(2025, 8, 16, 14, 30, 36, 103834, tzinfo=datetime.timezone.utc), execution_context={}, custom_fields={}, priority=None, retry_count=0, parent_agent_id=None, tags=[])) == {'action_plan_summary': 'Implement cost optimization strategies to reduce monthly spend by 30%', 'total_estimated_time': '4-6 weeks', 'required_approvals': ['Engineering Manager', 'Finance Team'], 'actions': [{'step_id': '1', 'description': 'Implement model caching system', 'estimated_duration': '2 weeks', 'priority': 'high'}, {'step_id': '2', 'description': 'Switch to cost-effective models', 'estimated_duration': '1 week', 'priority': 'medium'}], 'execution_timeline': [{'phase': 'Planning', 'duration': '1 week'}, {'phase': 'Implementation', 'duration': '3 weeks'}, {'phase': 'Testing', 'duration': '1 week'}], 'supply_config_updates': [{'config_type': 'model_routing', 'changes': ['Add cache layer']}], 'post_implementation': {'monitoring_period': '30 days', 'success_metrics': ['Cost reduction %', 'Performance impact'], 'optimization_review_schedule': 'Weekly'}, 'cost_benefit_analysis': {'implementation_cost': {'effort_hours': 200, 'resource_cost': 25000}, 'expected_benefits': {'cost_savings_per_month': 5000, 'performance_improvement_percentage': 15, 'roi_months': 5}}}
- [FAIL] TESTS FAILED with exit code 2 after 14.13s


---
*Generated by Netra AI Unified Test Runner v3.0*
