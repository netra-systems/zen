# Netra AI Platform - Test Report

**Generated:** 2025-08-17T19:16:56.629019  
**Test Level:** integration - Integration tests for component interaction (3-5 minutes)  
**Purpose:** Feature validation, API testing

## Test Summary

**Total Tests:** 47  
**Passed:** 44  
**Failed:** 3  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 47 | 44 | 3 | 0 | 0 | 33.56s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.32s | [FAILED] |

## Environment and Configuration

- **Test Level:** integration
- **Description:** Integration tests for component interaction (3-5 minutes)
- **Purpose:** Feature validation, API testing
- **Timeout:** 300s
- **Coverage Enabled:** Yes
- **Total Duration:** 33.88s
- **Exit Code:** 2

### Backend Configuration
```
--category integration -v --coverage --fail-fast --parallel=4 --markers not real_services
```

### Frontend Configuration
```
--category integration
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: integration
  Parallel: 4
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest integration_tests app/tests/routes -vv -n 4 -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 -m not real_services -p test_framework.pytest_bad_test_plugin --test-component backend
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
4 workers [174 items]

scheduling tests via LoadScheduling

app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_multi_modal_input 
app\test_app.py::test_read_main <- ..\integration_tests\test_app.py 
app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_bulk_operations 
app\test_health.py::test_ready_endpoint_clickhouse_failure <- ..\integration_tests\test_health.py 
[gw2][36m [  0%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_multi_modal_input 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_performance_metrics 
[gw3][36m [  1%] [0m[32mPASSED[0m app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_bulk_operations 
app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_system_settings 
[gw2][36m [  1%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_performance_metrics 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_fallback_mechanisms 
[gw2][36m [  2%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_fallback_mechanisms 
[gw3][36m [  2%] [0m[32mPASSED[0m app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_system_settings 
app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_audit_log_access 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_websocket_integration 
[gw3][36m [  3%] [0m[32mPASSED[0m app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_audit_log_access 
[gw2][36m [  4%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_websocket_integration 
app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_security_validation 
app\tests\routes\test_apex_optimizer_agent_route.py::test_apex_optimizer_agent[I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.] 
[gw3][36m [  4%] [0m[32mPASSED[0m app\tests\routes\test_admin_routes.py::TestAdminRoute::test_admin_security_validation 
[gw2][36m [  5%] [0m[32mPASSED[0m app\tests\routes\test_apex_optimizer_agent_route.py::test_apex_optimizer_agent[I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.] 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_message_processing 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_metrics 
[gw0][36m [  5%] [0m[32mPASSED[0m app\test_app.py::test_read_main <- ..\integration_tests\test_app.py 
[gw2][36m [  6%] [0m[32mPASSED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_metrics 
app\test_app.py::test_generation_api <- ..\integration_tests\test_app.py 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_invalidation 
[gw3][36m [  6%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_message_processing 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_streaming_response 
[gw2][36m [  7%] [0m[32mPASSED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_invalidation 
[gw3][36m [  8%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_streaming_response 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_selective_cache_invalidation 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_error_handling 
[gw2][36m [  8%] [0m[32mPASSED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_selective_cache_invalidation 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_performance_monitoring 
[gw3][36m [  9%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_error_handling 
[gw2][36m [  9%] [0m[32mPASSED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_performance_monitoring 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_message_validation 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_size_management 
[gw2][36m [ 10%] [0m[32mPASSED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_size_management 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_warm_up 
[gw2][36m [ 10%] [0m[32mPASSED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_warm_up 
app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_health_check 
[gw0][36m [ 11%] [0m[32mPASSED[0m app\test_app.py::test_generation_api <- ..\integration_tests\test_app.py 
app\test_app.py::test_analysis_api <- ..\integration_tests\test_app.py 
[gw0][36m [ 12%] [0m[32mPASSED[0m app\test_app.py::test_analysis_api <- ..\integration_tests\test_app.py 
[gw3][36m [ 12%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_message_validation 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_context_management 
[gw3][36m [ 13%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_context_management 
app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_rate_limiting 
app\test_generation_service.py::test_content_generation_with_custom_table <- ..\integration_tests\test_generation_service.py 
[gw2][36m [ 13%] [0m[31mFAILED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_health_check 
[gw0][36m [ 14%] [0m[32mPASSED[0m app\test_generation_service.py::test_content_generation_with_custom_table <- ..\integration_tests\test_generation_service.py 
app\test_generation_service.py::test_synthetic_data_generation_with_table_selection <- ..\integration_tests\test_generation_service.py 
[gw3][36m [ 14%] [0m[32mPASSED[0m app\tests\routes\test_agent_routes.py::TestAgentRoute::test_agent_rate_limiting 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_retrieval 
[gw3][36m [ 15%] [0m[32mPASSED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_retrieval 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_update_validation 
[gw3][36m [ 16%] [0m[32mPASSED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_update_validation 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_persistence 
[gw3][36m [ 16%] [0m[32mPASSED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_persistence 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_validation_rules 
[gw0][36m [ 17%] [0m[32mPASSED[0m app\test_generation_service.py::test_synthetic_data_generation_with_table_selection <- ..\integration_tests\test_generation_service.py 
app\test_generation_service.py::test_save_and_get_corpus <- ..\integration_tests\test_generation_service.py 
[gw3][36m [ 17%] [0m[32mPASSED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_validation_rules 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_environment_specific 
[gw0][36m [ 18%] [0m[32mPASSED[0m app\test_generation_service.py::test_save_and_get_corpus <- ..\integration_tests\test_generation_service.py 
app\test_generation_service.py::test_run_synthetic_data_generation_job_e2e <- ..\integration_tests\test_generation_service.py 
[gw3][36m [ 18%] [0m[32mPASSED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_environment_specific 
[gw0][36m [ 19%] [0m[32mPASSED[0m app\test_generation_service.py::test_run_synthetic_data_generation_job_e2e <- ..\integration_tests\test_generation_service.py 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_feature_flags 
[gw3][36m [ 20%] [0m[32mPASSED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_feature_flags 
app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_backup_and_restore 
[gw3][36m [ 20%] [0m[31mFAILE...(truncated)
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
- [gw2][36m [ 13%] [0m[31mFAILED[0m app\tests\routes\test_cache_routes.py::TestLLMCacheRoute::test_cache_health_check
- [gw3][36m [ 20%] [0m[31mFAILED[0m app\tests\routes\test_config_routes.py::TestConfigRoute::test_config_backup_and_restore
- [gw0][36m [ 21%] [0m[31mFAILED[0m app\test_health.py::test_live_endpoint <- ..\integration_tests\test_health.py
- ERROR    | logging:handle:1028 | Task was destroyed but it is pending!
- 2025-08-17 19:16:47.752 | ERROR    | logging:handle:1028 | Task was destroyed but it is pending!
- [1m[31mERROR   [0m asyncio:base_events.py:1821 Task was destroyed but it is pending!
- [1m[31mERROR   [0m asyncio:base_events.py:1821 Task was destroyed but it is pending!
- [31mFAILED[0m app\tests\routes\test_cache_routes.py::[1mTestLLMCacheRoute::test_cache_health_check[0m - AttributeError: <module 'app.services.llm_cache_service' from 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\app\\services\\llm_cache_service.py'> does not have the attribute 'health_check'
- [31mFAILED[0m app\tests\routes\test_config_routes.py::[1mTestConfigRoute::test_config_backup_and_restore[0m - ImportError: cannot import name 'backup_config' from 'app.routes.config' (C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app\routes\config.py)
- [31mFAILED[0m app\test_health.py::[1mtest_live_endpoint[0m - AssertionError: assert {'status': 'healthy', 'service': 'netra-ai-platform', 'version': '1.0.0', 'timestamp': '2025-08-18T02:16:47.762739Z', 'environment': 'development'} == {'status': 'healthy', 'service': 'netra-ai-platform'}
- [FAIL] TESTS FAILED with exit code 2 after 32.11s


---
*Generated by Netra AI Unified Test Runner v3.0*
