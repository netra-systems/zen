# Netra AI Platform - Test Report

**Generated:** 2025-08-16T06:39:19.929286  
**Test Level:** unit - Unit tests for isolated components (1-2 minutes)  
**Purpose:** Development validation, component testing

## Test Summary

**Total Tests:** 811  
**Passed:** 787  
**Failed:** 1  
**Skipped:** 23  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 811 | 787 | 1 | 23 | 0 | 67.03s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.23s | [FAILED] |

## Environment and Configuration

- **Test Level:** unit
- **Description:** Unit tests for isolated components (1-2 minutes)
- **Purpose:** Development validation, component testing
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 67.26s
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
  pytest app/tests/services app/tests/core -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services
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
4 workers [2440 items]

scheduling tests via LoadScheduling

app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_geo_distributed_simulation 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_mixed_field_type_patterns 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_geo_distributed_simulation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_adaptive_generation_feedback 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_adaptive_generation_feedback 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_multi_model_workload_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_compliance_aware_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_cost_optimized_generation 
app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
[gw1][36m [  0%] [0m[33mSKIPPED[0m app\tests\services\synthetic_data\test_advanced_features.py::TestAdvancedFeatures::test_versioned_corpus_generation 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_mixed_field_type_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_caching_functionality 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_execution 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_caching_functionality 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_large_query_handling 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_agent_run_with_model_dump_fallback 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_temporal_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_start_agent 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_tool_invocations 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_errors 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_large_query_handling 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_user_message 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_special_character_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_trace_hierarchies 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_special_character_patterns 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_whitespace_handling_patterns 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_stop_agent 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_domain_specific 
[gw0][36m [  0%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_whitespace_handling_patterns 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_logging_and_debugging_support 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_message_handling_unknown_type 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_distribution 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_not_found 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_logging_and_debugging_support 
app\tests\services\test_clickhouse_regex_patterns.py::TestRegexPatternCoverage::test_case_variation_patterns 
app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_with_custom_tools 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\services\agents\test_tools.py::test_tool_dispatcher_tool_error 
app\tests\services\synthetic_data\test_advanced_generation.py::TestAdvancedGenerationMethods::test_generate_incremental 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\services\test_agent_service_orchestration_basic.py::TestAgentServiceOrchestration::test_websocket_disconnect_handling 
app\tests\services\ape...(truncated)
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
- [gw2][36m [ 17%] [0m[31mFAILED[0m app\tests\services\test_clickhouse_query_validation.py::TestClickHouseQueryValidator::test_nested_field_access_warning
- [31mFAILED[0m app\tests\services\test_clickhouse_query_validation.py::[1mTestClickHouseQueryValidator::test_nested_field_access_warning[0m - AssertionError: assert 'nested' in 'query uses incorrect array syntax. use arrayelement() instead of []'
- [FAIL] TESTS FAILED with exit code 2 after 66.34s


---
*Generated by Netra AI Unified Test Runner v3.0*
