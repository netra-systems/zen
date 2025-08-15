# Netra AI Platform - Test Report

**Generated:** 2025-08-15T14:12:53.467508  
**Test Level:** critical - Critical path tests only (1-2 minutes)  
**Purpose:** Essential functionality verification

## Test Summary

**Total Tests:** 85  
**Passed:** 85  
**Failed:** 0  
**Skipped:** 0  
**Errors:** 0  
**Overall Status:** [FAILED]

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | 85 | 85 | 0 | 0 | 0 | 33.73s | [FAILED] |
| Frontend  | 0 | 0 | 0 | 0 | 0 | 0.00s | [SKIPPED] |

## Coverage Summary

**Overall Coverage:** 23.3%
**Backend Coverage:** 23.3%  

## Environment and Configuration

- **Test Level:** critical
- **Description:** Critical path tests only (1-2 minutes)
- **Purpose:** Essential functionality verification
- **Timeout:** 120s
- **Coverage Enabled:** Yes
- **Total Duration:** 33.73s
- **Exit Code:** 1

### Backend Configuration
```
--category critical --fail-fast --coverage
```

### Frontend Configuration
```
--category smoke
```

## Test Output

### Backend Output
```
Loaded test environment from C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\.env.test
================================================================================
NETRA AI PLATFORM - BACKEND TEST RUNNER
================================================================================
Test Configuration:
  Category: critical
  Parallel: disabled
  Coverage: enabled
  Fail Fast: enabled
  Environment: testing

Running command:
  pytest app/tests/test_api_endpoints_critical.py app/tests/test_agent_service_critical.py -v -x --maxfail=1 --cov=app --cov-report=html:reports/coverage/html --cov-report=term-missing --cov-report=json:reports/coverage/coverage.json --cov-fail-under=70 --tb=short --asyncio-mode=auto --color=yes --strict-markers --disable-warnings -p no:warnings
================================================================================
[1m============================= test session starts =============================[0m
platform win32 -- Python 3.12.4, pytest-8.4.1, pluggy-1.6.0 -- C:\Users\antho\miniconda3\python.exe
cachedir: .pytest_cache
metadata: {'Python': '3.12.4', 'Platform': 'Windows-11-10.0.26100-SP0', 'Packages': {'pytest': '8.4.1', 'pluggy': '1.6.0'}, 'Plugins': {'anyio': '4.9.0', 'Faker': '37.4.2', 'langsmith': '0.4.10', 'asyncio': '0.21.1', 'cov': '6.2.1', 'html': '4.1.1', 'json-report': '1.5.0', 'metadata': '3.1.1', 'mock': '3.14.1', 'timeout': '2.4.0', 'xdist': '3.8.0', 'typeguard': '4.4.4'}}
rootdir: C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\app
configfile: pytest.ini
plugins: anyio-4.9.0, Faker-37.4.2, langsmith-0.4.10, asyncio-0.21.1, cov-6.2.1, html-4.1.1, json-report-1.5.0, metadata-3.1.1, mock-3.14.1, timeout-2.4.0, xdist-3.8.0, typeguard-4.4.4
asyncio: mode=Mode.AUTO
[1mcollecting ... [0mcollected 85 items

app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_health_endpoints [32mPASSED[0m[32m [  1%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_health_ready_endpoint [32mPASSED[0m[32m [  2%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_login_endpoint [32mPASSED[0m[32m [  3%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_register_endpoint [32mPASSED[0m[32m [  4%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_pagination_basic [32mPASSED[0m[32m [  5%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_pagination_metadata [32mPASSED[0m[32m [  7%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_rate_limiting_exceeded [32mPASSED[0m[32m [  8%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_rate_limiting_headers [32mPASSED[0m[32m [  9%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_authentication_token_validation [32mPASSED[0m[32m [ 10%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_health_service_status [32mPASSED[0m[32m [ 11%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_authentication_error_handling [32mPASSED[0m[32m [ 12%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_registration_validation [32mPASSED[0m[32m [ 14%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_pagination_edge_cases [32mPASSED[0m[32m [ 15%][0m
app\tests\test_api_endpoints_critical.py::TestAPICoreEndpointsCritical::test_rate_limiting_recovery [32mPASSED[0m[32m [ 16%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_create_thread [32mPASSED[0m[32m [ 17%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_get_user_threads [32mPASSED[0m[32m [ 18%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_creation_validation [32mPASSED[0m[32m [ 20%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_send_message [32mPASSED[0m[32m [ 21%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_get_thread_messages [32mPASSED[0m[32m [ 22%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_role_validation [32mPASSED[0m[32m [ 23%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_content_validation [32mPASSED[0m[32m [ 24%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_listing_pagination [32mPASSED[0m[32m [ 25%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_timestamp_validation [32mPASSED[0m[32m [ 27%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_id_validation [32mPASSED[0m[32m [ 28%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_empty_thread_list [32mPASSED[0m[32m [ 29%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_order_consistency [32mPASSED[0m[32m [ 30%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_thread_title_handling [32mPASSED[0m[32m [ 31%][0m
app\tests\test_api_endpoints_critical.py::TestAPIThreadsMessagesCritical::test_message_context_preservation [32mPASSED[0m[32m [ 32%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_query_endpoint [32mPASSED[0m[32m [ 34%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_metadata_validation [32mPASSED[0m[32m [ 35%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_synthetic_data_generation [32mPASSED[0m[32m [ 36%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_job_tracking [32mPASSED[0m[32m [ 37%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_get_endpoint [32mPASSED[0m[32m [ 38%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_features_validation [32mPASSED[0m[32m [ 40%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_update_endpoint [32mPASSED[0m[32m [ 41%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_context_handling [32mPASSED[0m[32m [ 42%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_type_validation [32mPASSED[0m[32m [ 43%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_processing_time_tracking [32mPASSED[0m[32m [ 44%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_limits_validation [32mPASSED[0m[32m [ 45%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_format_options [32mPASSED[0m[32m [ 47%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_agent_multi_agent_orchestration [32mPASSED[0m[32m [ 48%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_configuration_environment_detection [32mPASSED[0m[32m [ 49%][0m
app\tests\test_api_endpoints_critical.py::TestAPIAgentGenerationCritical::test_generation_count_validation [32mPASSED[0m[32m [ 50%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_bad_request_error [32mPASSED[0m[32m [ 51%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_unauthorized_error [32mPASSED[0m[32m [ 52%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_forbidden_error [32mPASSED[0m[32m [ 54%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_not_found_error [32mPASSED[0m[32m [ 55%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_internal_server_error [32mPASSED[0m[32m [ 56%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_validation_error_detail [32mPASSED[0m[32m [ 57%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_authentication_invalid_credentials [32mPASSED[0m[32m [ 58%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_permission_insufficient_rights [32mPASSED[0m[32m [ 60%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_resource_not_found_specific [32mPASSED[0m[32m [ 61%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_malformed_json_error [32mPASSED[0m[32m [ 62%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_missing_required_headers [32mPASSED[0m[32m [ 63%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_invalid_token_format [32mPASSED[0m[32m [ 64%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_expired_token_error [32mPASSED[0m[32m [ 65%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_method_not_allowed [32mPASSED[0m[32m [ 67%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_content_type_validation [32mPASSED[0m[32m [ 68%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_request_timeout_error [32mPASSED[0m[32m [ 69%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_payload_too_large [32mPASSED[0m[32m [ 70%][0m
app\tests\test_api_endpoints_critical.py::TestAPIErrorHandlingCritical::test_service_unavailable [32mPASSED[0m[32m [ 71%][0m
app\tests\test_api_endpoints_critical.p...(truncated)
```

### Frontend Output
```

```
---
*Generated by Netra AI Unified Test Runner v3.0*
