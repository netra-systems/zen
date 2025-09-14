# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-14 05:49:53
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 20
- **Passed:** 1 (5.0%)
- **Failed:** 9 (45.0%)
- **Skipped:** 10
- **Duration:** 10.59 seconds
- **Pass Rate:** 5.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_complete_user_registration_to_authenticated_action | FAIL failed | 0.697s | test_auth_complete_workflows.py |
| test_oauth_login_flow_with_provider_simulation | FAIL failed | 0.386s | test_auth_complete_workflows.py |
| test_jwt_token_refresh_and_lifecycle_management | FAIL failed | 0.130s | test_auth_complete_workflows.py |
| test_multi_step_authentication_with_session_persistence | FAIL failed | 0.608s | test_auth_complete_workflows.py |
| test_authentication_failure_recovery_and_error_handling | FAIL failed | 2.301s | test_auth_complete_workflows.py |
| test_auth_google_login_route_returns_404 | SKIP skipped | 0.000s | test_auth_routes.py |
| test_multiple_oauth_routes_missing_404_pattern | SKIP skipped | 0.000s | test_auth_routes.py |
| test_auth_service_route_registration_incomplete | SKIP skipped | 0.000s | test_auth_routes.py |
| test_auth_service_route_mapping_configuration_error | SKIP skipped | 0.000s | test_auth_routes.py |
| test_auth_service_oauth_blueprint_not_registered | SKIP skipped | 0.000s | test_auth_routes.py |
| test_oauth_route_handler_import_or_dependency_missing | SKIP skipped | 0.000s | test_auth_routes.py |
| test_staging_auth_registration_business_flow | SKIP skipped | 0.281s | test_auth_service_business_flows_api_fix.py |
| test_staging_auth_login_business_flow | SKIP skipped | 0.001s | test_auth_service_business_flows_api_fix.py |
| test_staging_token_validation_business_flow | SKIP skipped | 0.001s | test_auth_service_business_flows_api_fix.py |
| test_staging_auth_service_health_check | SKIP skipped | 0.001s | test_auth_service_business_flows_api_fix.py |
| test_docker_api_signature_fails_but_staging_auth_works | PASS passed | 0.429s | test_auth_service_business_flows_api_fix.py |
| test_staging_auth_service_health_during_startup_race | FAIL failed | 0.547s | test_auth_service_startup_race_condition.py |
| test_staging_oauth_initialization_race_condition | FAIL failed | 0.239s | test_auth_service_startup_race_condition.py |
| test_staging_database_connectivity_during_startup_race | FAIL failed | 0.614s | test_auth_service_startup_race_condition.py |
| test_staging_full_startup_race_condition_reproduction | FAIL failed | 0.944s | test_auth_service_startup_race_condition.py |

## Failed Tests Details

### FAILED: test_complete_user_registration_to_authenticated_action
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_complete_workflows.py
- **Duration:** 0.697s
- **Error:** tests\e2e\staging\test_auth_complete_workflows.py:183: in test_complete_user_registration_to_authenticated_action
    assert resp.status == 200, f"Profile access failed: {resp.status}"
E   AssertionError: Profile access failed: 500
E   assert 500 == 200
E    +  where 500 = <ClientResponse(https://api.staging.netrasystems.ai/api/v1/user/profile) [500 Internal Server Error]>\n<CIMultiDictProxy('Content-Type': 'application/json', 'x-cloud-trace-context': '3659506dfea5f636ccab9974cea710e2', 'Date': ...

### FAILED: test_oauth_login_flow_with_provider_simulation
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_complete_workflows.py
- **Duration:** 0.386s
- **Error:** tests\e2e\staging\test_auth_complete_workflows.py:307: in test_oauth_login_flow_with_provider_simulation
    assert resp.status == 200, f"OAuth token validation failed: {resp.status}"
E   AssertionError: OAuth token validation failed: 405
E   assert 405 == 200
E    +  where 405 = <ClientResponse(https://auth.staging.netrasystems.ai/auth/validate) [405 Method Not Allowed]>\n<CIMultiDictProxy('Allow': 'POST', 'Content-Type': 'application/json', 'x-service-name': 'auth-service', 'x-service-version'...

### FAILED: test_jwt_token_refresh_and_lifecycle_management
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_complete_workflows.py
- **Duration:** 0.130s
- **Error:** tests\e2e\staging\test_auth_complete_workflows.py:406: in test_jwt_token_refresh_and_lifecycle_management
    assert resp.status == 200, f"Initial token validation failed: {resp.status}"
E   AssertionError: Initial token validation failed: 405
E   assert 405 == 200
E    +  where 405 = <ClientResponse(https://auth.staging.netrasystems.ai/auth/validate) [405 Method Not Allowed]>\n<CIMultiDictProxy('Allow': 'POST', 'Content-Type': 'application/json', 'x-service-name': 'auth-service', 'x-service-ver...

### FAILED: test_multi_step_authentication_with_session_persistence
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_complete_workflows.py
- **Duration:** 0.608s
- **Error:** tests\e2e\staging\test_auth_complete_workflows.py:578: in test_multi_step_authentication_with_session_persistence
    assert resp.status == 200, f"Secondary validation failed: {resp.status}"
E   AssertionError: Secondary validation failed: 405
E   assert 405 == 200
E    +  where 405 = <ClientResponse(https://auth.staging.netrasystems.ai/auth/validate) [405 Method Not Allowed]>\n<CIMultiDictProxy('Allow': 'POST', 'Content-Type': 'application/json', 'x-service-name': 'auth-service', 'x-service-ver...

### FAILED: test_authentication_failure_recovery_and_error_handling
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_complete_workflows.py
- **Duration:** 2.301s
- **Error:** tests\e2e\staging\test_auth_complete_workflows.py:897: in test_authentication_failure_recovery_and_error_handling
    assert result.business_value_delivered, "Auth failure recovery did not deliver business value"
E   AssertionError: Auth failure recovery did not deliver business value
E   assert False
E    +  where False = AuthWorkflowTestResult(success=True, user_id='recovery-test-user', email='failure-test-d73cf191@staging-failure.com', jwt_token='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiO...

### FAILED: test_staging_auth_service_health_during_startup_race
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_service_startup_race_condition.py
- **Duration:** 0.547s
- **Error:** tests\e2e\staging\test_auth_service_startup_race_condition.py:195: in test_staging_auth_service_health_during_startup_race
    self.assertGreater(total_race_failures, 0,
test_framework\ssot\base_test_case.py:554: in assertGreater
    assert first > second, msg or f"Expected {first} > {second}"
           ^^^^^^^^^^^^^^
E   AssertionError: Expected auth service startup race condition failures in staging. Got 0 race condition failures out of 40 checks....

### FAILED: test_staging_oauth_initialization_race_condition
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_service_startup_race_condition.py
- **Duration:** 0.239s
- **Error:** tests\e2e\staging\test_auth_service_startup_race_condition.py:309: in test_staging_oauth_initialization_race_condition
    self.assertGreater(total_oauth_race_failures, 0,
test_framework\ssot\base_test_case.py:554: in assertGreater
    assert first > second, msg or f"Expected {first} > {second}"
           ^^^^^^^^^^^^^^
E   AssertionError: Expected OAuth initialization race condition failures in staging. Got 0 failures out of 24 operations....

### FAILED: test_staging_database_connectivity_during_startup_race
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_service_startup_race_condition.py
- **Duration:** 0.614s
- **Error:** tests\e2e\staging\test_auth_service_startup_race_condition.py:428: in test_staging_database_connectivity_during_startup_race
    self.assertGreater(db_race_failures, 0,
test_framework\ssot\base_test_case.py:554: in assertGreater
    assert first > second, msg or f"Expected {first} > {second}"
           ^^^^^^^^^^^^^^
E   AssertionError: Expected database connectivity race condition failures in staging. Got 0 database-related failures out of 36 checks....

### FAILED: test_staging_full_startup_race_condition_reproduction
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_auth_service_startup_race_condition.py
- **Duration:** 0.944s
- **Error:** tests\e2e\staging\test_auth_service_startup_race_condition.py:559: in test_staging_full_startup_race_condition_reproduction
    self.assertTrue(False, f"Comprehensive staging startup race condition reproduced: "
test_framework\ssot\base_test_case.py:538: in assertTrue
    assert expr, msg or f"Expected True, got {expr}"
           ^^^^
E   AssertionError: Comprehensive staging startup race condition reproduced: 15 total failures across all auth service components. Service unavailable responses: ...

## Pytest Output Format

```
test_auth_complete_workflows.py::test_complete_user_registration_to_authenticated_action FAILED
test_auth_complete_workflows.py::test_oauth_login_flow_with_provider_simulation FAILED
test_auth_complete_workflows.py::test_jwt_token_refresh_and_lifecycle_management FAILED
test_auth_complete_workflows.py::test_multi_step_authentication_with_session_persistence FAILED
test_auth_complete_workflows.py::test_authentication_failure_recovery_and_error_handling FAILED
test_auth_routes.py::test_auth_google_login_route_returns_404 SKIPPED
test_auth_routes.py::test_multiple_oauth_routes_missing_404_pattern SKIPPED
test_auth_routes.py::test_auth_service_route_registration_incomplete SKIPPED
test_auth_routes.py::test_auth_service_route_mapping_configuration_error SKIPPED
test_auth_routes.py::test_auth_service_oauth_blueprint_not_registered SKIPPED
test_auth_routes.py::test_oauth_route_handler_import_or_dependency_missing SKIPPED
test_auth_service_business_flows_api_fix.py::test_staging_auth_registration_business_flow SKIPPED
test_auth_service_business_flows_api_fix.py::test_staging_auth_login_business_flow SKIPPED
test_auth_service_business_flows_api_fix.py::test_staging_token_validation_business_flow SKIPPED
test_auth_service_business_flows_api_fix.py::test_staging_auth_service_health_check SKIPPED
test_auth_service_business_flows_api_fix.py::test_docker_api_signature_fails_but_staging_auth_works PASSED
test_auth_service_startup_race_condition.py::test_staging_auth_service_health_during_startup_race FAILED
test_auth_service_startup_race_condition.py::test_staging_oauth_initialization_race_condition FAILED
test_auth_service_startup_race_condition.py::test_staging_database_connectivity_during_startup_race FAILED
test_auth_service_startup_race_condition.py::test_staging_full_startup_race_condition_reproduction FAILED

==================================================
1 passed, 9 failed, 10 skipped in 10.59s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Authentication | 17 | 1 | 7 | 5.9% |
| Data | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
