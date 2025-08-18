# Netra AI Platform - Test Report

**Generated:** 2025-08-17T18:06:35.237516  
**Test Level:** agents - Agent-specific unit tests (2-3 minutes)  
**Purpose:** Quick validation of agent functionality during development

## Test Summary

**Total Tests:** 26  
**Passed:** 22  
**Failed:** 3  
**Skipped:** 0  
**Errors:** 1  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 26 | 22 | 3 | 0 | 1 | 22.63s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Environment and Configuration

- **Test Level:** agents
- **Description:** Agent-specific unit tests (2-3 minutes)
- **Purpose:** Quick validation of agent functionality during development
- **Timeout:** 180s
- **Coverage Enabled:** No
- **Total Duration:** 22.63s
- **Exit Code:** 2

### Backend Configuration
```
--category agent -v --fail-fast --parallel=4 --markers not real_services
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
  Category: agent
  Parallel: 4
  Coverage: disabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/agents app/tests/services/agents app/tests/services/apex_optimizer_agent -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings -m not real_services -p test_framework.pytest_bad_test_plugin --test-component backend
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
4 workers [791 items]

scheduling tests via LoadScheduling

app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_identify_outliers_zscore_no_variance <- tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_processing.py::TestDataSubAgentProcessing::test_process_with_cache_different_keys 
app\tests\agents\test_agent_e2e_critical_collab.py::TestAgentE2ECriticalCollaboration::test_7_authentication_and_authorization 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_insufficient_data 
[gw3][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_processing.py::TestDataSubAgentProcessing::test_process_with_cache_different_keys 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_identify_outliers_zscore_no_variance <- tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_processing.py::TestDataSubAgentProcessing::test_process_and_stream 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_identify_outliers_invalid_method <- tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestAnalysisEngine::test_identify_outliers_invalid_method <- tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_initialization <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_initialization <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_insufficient_data 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_no_time_variation 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_initialization_redis_failure <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_no_time_variation 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_increasing 
[gw1][36m [  0%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_increasing 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_initialization_redis_failure <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_decreasing 
app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_get_cached_schema_success <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_decreasing 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_weak 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_trend_weak 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_insufficient_data 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_insufficient_data 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_insufficient_hourly_coverage 
[gw0][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_agent_e2e_critical_collab.py::TestAgentE2ECriticalCollaboration::test_7_authentication_and_authorization 
[gw2][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_get_cached_schema_success <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_insufficient_hourly_coverage 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_with_pattern 
[gw1][36m [  1%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_with_pattern 
app\tests\agents\test_agent_e2e_critical_collab.py::TestAgentE2ECriticalCollaboration::test_8_multi_agent_collaboration 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_no_pattern 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_detect_seasonality_no_pattern 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_insufficient_data 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_insufficient_data 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_iqr_method 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_iqr_method 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_zscore_method 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_zscore_method 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_zscore_no_variance 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_zscore_no_variance 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_invalid_method 
[gw1][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_analysis_engine.py::TestAnalysisEngine::test_identify_outliers_invalid_method 
app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_analysis.py::TestDataSubAgentAnalysis::test_analyze_performance_metrics_no_data 
[gw0][36m [  2%] [0m[32mPASSED[0m app\tests\agents\test_agent_e2e_critical_collab.py::TestAgentE2ECriticalCollaboration::test_8_multi_agent_collaboration 
app\tests\agents\test_agent_e2e_critical_core.py::TestAgentE2ECriticalCore::test_1_complete_agent_lifecycle_request_to_completion 
[gw3][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_processing.py::TestDataSubAgentProcessing::test_process_and_stream 
[gw0][36m [  3%] [0m[31mFAILED[0m app\te...(truncated)
```

### Frontend Output
```

```

## Error Summary

### Backend Errors
- [gw2][36m [  1%] [0m[31mERROR[0m app\tests\agents\test_data_sub_agent_comprehensive.py::TestDataSubAgentBasic::test_get_cached_schema_success <- tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_basic.py
- [gw3][36m [  2%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_processing.py::TestDataSubAgentProcessing::test_process_and_stream
- [gw0][36m [  3%] [0m[31mFAILED[0m app\tests\agents\test_agent_e2e_critical_core.py::TestAgentE2ECriticalCore::test_1_complete_agent_lifecycle_request_to_completion
- [gw1][36m [  3%] [0m[31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_analysis.py::TestDataSubAgentAnalysis::test_analyze_performance_metrics_minute_aggregation Loaded .env file from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env
- =================================== ERRORS ====================================
- [31m[1m___ ERROR at setup of TestDataSubAgentBasic.test_get_cached_schema_success ____[0m
- 2025-08-17 18:06:31.757 | ERROR    | app.core.unified_logging:_emit_log:115 | ClickHouse query failed: HTTPDriver for https://xedvrr4c3r.us-central1.gcp.clickhouse.cloud:8443 received ClickHouse error code 386
- 2025-08-17 18:06:32.372 | ERROR    | logging:handle:1028 | Task was destroyed but it is pending!
- [31m[1mERROR   [0m asyncio:base_events.py:1821 Task was destroyed but it is pending!
- [31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_processing.py::[1mTestDataSubAgentProcessing::test_process_and_stream[0m - KeyError: 'processed'
- [31mFAILED[0m app\tests\agents\test_agent_e2e_critical_core.py::[1mTestAgentE2ECriticalCore::test_1_complete_agent_lifecycle_request_to_completion[0m - ValueError: not enough values to unpack (expected 2, got 0)
- [31mFAILED[0m app\tests\agents\test_data_sub_agent_comprehensive_suite\test_data_sub_agent_analysis.py::[1mTestDataSubAgentAnalysis::test_analyze_performance_metrics_minute_aggregation[0m - AssertionError: assert 'time_range' in {'status': 'no_data', 'message': 'No performance metrics found for the specified criteria'}
- [31mERROR[0m app\tests\agents\test_data_sub_agent_comprehensive.py::[1mTestDataSubAgentBasic::test_get_cached_schema_success[0m
- [FAIL] TESTS FAILED with exit code 2 after 21.59s


---
*Generated by Netra AI Unified Test Runner v3.0*
