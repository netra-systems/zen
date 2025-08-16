# Netra AI Platform - Test Report

**Generated:** 2025-08-15T22:27:13.099631  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 327  
**Passed:** 309  
**Failed:** 3  
**Skipped:** 15  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 327 | 309 | 3 | 15 | 0 | 68.98s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.23s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 69.22s
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
4 workers [2444 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_geo_distributed_simulation 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_advanced_regex_patterns 
[gw2][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_geo_distributed_simulation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_adaptive_generation_feedback 
[gw2][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_adaptive_generation_feedback 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
[gw2][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
[gw2][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
[gw2][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
[gw2][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_incremental 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_concurrent_agent_execution 
[gw3][36m [  0%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_advanced_regex_patterns 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\test_tool_builder.py::test_tool_builder_and_dispatcher 
app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_concurrent_agent_execution 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_message_parsing_string_input 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_advanced_optimization_for_core_function.py::test_advanced_optimization_for_core_function_tool 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_basic 
app\tests\services\apex_optimizer_agent\tools\test_base.py::TestToolMetadata::test_tool_metadata_creation_full 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_...(truncated)
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
- [gw3][36m [  0%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_advanced_regex_patterns
- [gw0][36m [  6%] [0m[31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_policy_simulator.py::TestPolicySimulator::test_policy_simulator_async_behavior
- [gw1][36m [  8%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_array_syntax.py::TestClickHouseArraySyntaxFixer::test_mixed_correct_and_incorrect_syntax
- [31mFAILED[0m app\tests\services\test_clickhouse_regex_patterns.py::[1mTestRegexPatternCoverage::test_advanced_regex_patterns[0m - AssertionError: assert 'arrayElement(nested.very.deep.field, complex_expr)' in 'SELECT nested.very.arrayElement(deep.field, complex_expr) FROM table'
- [31mFAILED[0m app\tests\services\apex_optimizer_agent\tools\test_policy_simulator.py::[1mTestPolicySimulator::test_policy_simulator_async_behavior[0m - assert 0.0 >= 0.009
- [31mFAILED[0m app\tests\services\test_clickhouse_array_syntax.py::[1mTestClickHouseArraySyntaxFixer::test_mixed_correct_and_incorrect_syntax[0m - AssertionError: assert 'toFloat64OrZero(arrayElement(metrics.incorrect, 2))' in '\n            SELECT \n                toFloat64OrZero(arrayElement(metrics.correct, 1)) as correct_field,\n                arrayElement(metrics.incorrect, 2) as incorrect_field\n            FROM test_table\n        '
- [FAIL] TESTS FAILED with exit code 2 after 68.30s


---
*Generated by Netra AI Unified Test Runner v3.0*
