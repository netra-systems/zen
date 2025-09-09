# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-09 15:52:34
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 17
- **Passed:** 3 (17.6%)
- **Failed:** 2 (11.8%)
- **Skipped:** 12
- **Duration:** 5.51 seconds
- **Pass Rate:** 17.6%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_google_oauth_client_id_missing_from_environment | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_google_oauth_client_secret_missing_from_environment | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_configuration_incomplete_for_staging_deployment | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_google_authorization_url_construction_fails | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_token_exchange_endpoint_unreachable | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_redirect_uri_misconfiguration | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_scopes_configuration_incomplete | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_critical_environment_variables_missing | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_service_url_configuration_mismatch | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_database_configuration_inconsistent_across_services | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_environment_variable_type_validation_failures | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_staging_specific_configuration_missing | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_staging_service_connectivity_and_health | FAIL failed | 0.616s | test_staging_configuration_validation.py |
| test_staging_authentication_configuration_validation | FAIL failed | 0.147s | test_staging_configuration_validation.py |
| test_staging_websocket_configuration_and_ssl | PASS passed | 3.529s | test_staging_configuration_validation.py |
| test_staging_environment_variables_validation | PASS passed | 0.000s | test_staging_configuration_validation.py |
| test_staging_api_endpoints_and_cors_validation | PASS passed | 0.927s | test_staging_configuration_validation.py |

## Failed Tests Details

### FAILED: test_staging_service_connectivity_and_health
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_staging_configuration_validation.py
- **Duration:** 0.616s
- **Error:** tests/e2e/staging/test_staging_configuration_validation.py:170: in test_staging_service_connectivity_and_health
    assert any("netra" in str(v).lower() or "netra" in str(k).lower()
E   AssertionError: Backend health endpoint doesn't identify as Netra service
E   assert False
E    +  where False = any(<generator object TestStagingConfigurationValidation.test_staging_service_connectivity_and_health.<locals>.<genexpr> at 0x115dba6c0>)...

### FAILED: test_staging_authentication_configuration_validation
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_staging_configuration_validation.py
- **Duration:** 0.147s
- **Error:** tests/e2e/staging/test_staging_configuration_validation.py:227: in test_staging_authentication_configuration_validation
    assert is_valid, "Generated JWT token failed validation with auth service"
E   AssertionError: Generated JWT token failed validation with auth service
E   assert False

During handling of the above exception, another exception occurred:
tests/e2e/staging/test_staging_configuration_validation.py:234: in test_staging_authentication_configuration_validation
    pytest.fail(f"J...

## Pytest Output Format

```
test_oauth_configuration.py::test_google_oauth_client_id_missing_from_environment SKIPPED
test_oauth_configuration.py::test_google_oauth_client_secret_missing_from_environment SKIPPED
test_oauth_configuration.py::test_oauth_configuration_incomplete_for_staging_deployment SKIPPED
test_oauth_configuration.py::test_oauth_google_authorization_url_construction_fails SKIPPED
test_oauth_configuration.py::test_oauth_token_exchange_endpoint_unreachable SKIPPED
test_oauth_configuration.py::test_oauth_redirect_uri_misconfiguration SKIPPED
test_oauth_configuration.py::test_oauth_scopes_configuration_incomplete SKIPPED
test_environment_configuration.py::test_critical_environment_variables_missing SKIPPED
test_environment_configuration.py::test_service_url_configuration_mismatch SKIPPED
test_environment_configuration.py::test_database_configuration_inconsistent_across_services SKIPPED
test_environment_configuration.py::test_environment_variable_type_validation_failures SKIPPED
test_environment_configuration.py::test_staging_specific_configuration_missing SKIPPED
test_staging_configuration_validation.py::test_staging_service_connectivity_and_health FAILED
test_staging_configuration_validation.py::test_staging_authentication_configuration_validation FAILED
test_staging_configuration_validation.py::test_staging_websocket_configuration_and_ssl PASSED
test_staging_configuration_validation.py::test_staging_environment_variables_validation PASSED
test_staging_configuration_validation.py::test_staging_api_endpoints_and_cors_validation PASSED

==================================================
3 passed, 2 failed, 12 skipped in 5.51s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 1 | 0 | 100.0% |
| Authentication | 8 | 0 | 1 | 0.0% |
| Security | 1 | 1 | 0 | 100.0% |
| Data | 1 | 0 | 0 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
