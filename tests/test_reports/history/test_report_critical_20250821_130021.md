# Netra AI Platform - Test Report

**Generated:** 2025-08-21T13:00:02.121062  
**Test Level:** critical - Critical path tests only (1-2 minutes)  

## 1. Test Summary

[FAILED] **OVERALL STATUS**

### Test Counts (Extracted from pytest output)
- **Total Tests:** 85
- **Passed:** 84 
- **Failed:** 1
- **Skipped:** 0
- **Errors:** 0

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 85 | 84 | 1 | 0 | 0 | 10.55s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## 3. Environment and Configuration

- **Test Level:** critical
- **Description:** Critical path tests only (1-2 minutes)
- **Purpose:** Essential functionality verification
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 10.55s
- **Exit Code:** 1

### Backend Configuration
```
--category critical --fail-fast --coverage
```

### Frontend Configuration
```
--category smoke
```

## 4. Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: critical
  Parallel: disabled
  Coverage: disabled
  Fail Fast: enabled
  Environment: test

Running command:
  pytest -c C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\pytest.ini netra_backend/tests/test_api_endpoints_critical.py netra_backend/tests/test_agent_service_critical.py -v -x --maxfail=1 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.5.3', 'langsmith': '0.4.15', 'asyncio': '1.1.0', 'cov': '6.2.1', 'mock': '3.14.1', 'xdist': '3.8.0', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'timeout': '2.4.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.5.3, langsmith-0.4.15, asyncio-1.1.0, cov-6.2.1, mock-3.14.1, xdist-3.8.0, html-4.1.1, json-report-1.5.0, metadata-3.1.1, timeout-2.4.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
[1mcollecting ... [0mcollected 85 items

netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_health_endpoints [32mPASSED[0m[32m [  1%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_health_ready_endpoint [32mPASSED[0m[32m [  2%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_login_endpoint [32mPASSED[0m[32m [  3%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_register_endpoint [32mPASSED[0m[32m [  4%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_pagination_basic [32mPASSED[0m[32m [  5%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_pagination_metadata [32mPASSED[0m[32m [  7%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_rate_limiting_exceeded [32mPASSED[0m[32m [  8%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_rate_limiting_headers [32mPASSED[0m[32m [  9%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_authentication_token_validation [32mPASSED[0m[32m [ 10%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_health_service_status [32mPASSED[0m[32m [ 11%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_authentication_error_handling [32mPASSED[0m[32m [ 12%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_registration_validation [32mPASSED[0m[32m [ 14%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_pagination_edge_cases [32mPASSED[0m[32m [ 15%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_rate_limiting_recovery [32mPASSED[0m[32m [ 16%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_create_thread [32mPASSED[0m[32m [ 17%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_get_user_threads [32mPASSED[0m[32m [ 18%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_creation_validation [32mPASSED[0m[32m [ 20%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_send_message [32mPASSED[0m[32m [ 21%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_get_thread_messages [32mPASSED[0m[32m [ 22%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_role_validation [32mPASSED[0m[32m [ 23%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_content_validation [32mPASSED[0m[32m [ 24%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_listing_pagination [32mPASSED[0m[32m [ 25%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_timestamp_validation [32mPASSED[0m[32m [ 27%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_id_validation [32mPASSED[0m[32m [ 28%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_empty_thread_list [32mPASSED[0m[32m [ 29%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_order_consistency [32mPASSED[0m[32m [ 30%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_title_handling [32mPASSED[0m[32m [ 31%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_context_preservation [32mPASSED[0m[32m [ 32%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_query_endpoint [32mPASSED[0m[32m [ 34%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_metadata_validation [32mPASSED[0m[32m [ 35%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_synthetic_data_generation [32mPASSED[0m[32m [ 36%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_job_tracking [32mPASSED[0m[32m [ 37%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_get_endpoint [32mPASSED[0m[32m [ 38%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_features_validation [32mPASSED[0m[32m [ 40%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_update_endpoint [32mPASSED[0m[32m [ 41%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_context_handling [32mPASSED[0m[32m [ 42%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_type_validation [32mPASSED[0m[32m [ 43%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_processing_time_tracking [32mPASSED[0m[32m [ 44%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_limits_validation [32mPASSED[0m[32m [ 45%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_format_options [32mPASSED[0m[32m [ 47%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_multi_agent_orchestration [32mPASSED[0m[32m [ 48%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_environment_detection [32mPASSED[0m[32m [ 49%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_count_validation [32mPASSED[0m[32m [ 50%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_bad_request_error [32mPASSED[0m[32m [ 51%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_unauthorized_error [32mPASSED[0m[32m [ 52%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_forbidden_error [32mPASSED[0m[32m [ 54%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_not_found_error [32mPASSED[0m[32m [ 55%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_internal_server_error [32mPASSED[0m[32m [ 56%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_validation_error_detail [32mPASSED[0m[32m [ 57%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_authentication_invalid_credentials [32mPASSED[0m[32m [ 58%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_permission_insufficient_rights [32mPASSED[0m[32m [ 60%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_resource_not_found_specific [32mPASSED[0m[32m [ 61%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_malformed_json_error [32mPASSED[0m[32m [ 62%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_missing_required_headers [32mPASSED[0m[32m [ 63%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_invalid_token_format [32mPASSED[0m[32m [ 64%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_expired_token_error [32mPASSED[0m[32m [ 65%][0m
netra_backend/tests/test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_method_not...(truncated)
```

### Frontend Output
```

```

## 5. Error Details

### Backend Errors
- netra_backend/tests/test_agent_service_critical.py::TestAgentServiceCritical::test_logging_integration [31mFAILED[0m[31m [100%][0m
- [31mFAILED[0m netra_backend/tests/test_agent_service_critical.py::[1mTestAgentServiceCritical::test_logging_integration[0m - AssertionError: assert 0 > 0
- [FAIL] TESTS FAILED with exit code 1 after 9.43s

---
*Generated by Netra AI Unified Test Runner v3.0*  
*Report structure follows SPEC/testing.xml requirements*
