# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-10 20:37:28
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 7
- **Passed:** 1 (14.3%)
- **Failed:** 4 (57.1%)
- **Skipped:** 2
- **Duration:** 0.65 seconds
- **Pass Rate:** 14.3%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_auth_service_actually_works_in_staging | SKIP skipped | 0.000s | test_golden_path_validation_staging_current.py |
| test_backend_service_actually_works_in_staging | SKIP skipped | 0.000s | test_golden_path_validation_staging_current.py |
| test_golden_path_validator_fails_despite_working_services | FAIL failed | 0.001s | test_golden_path_validation_staging_current.py |
| test_validator_prevents_successful_staging_deployment | FAIL failed | 0.348s | test_golden_path_validation_staging_current.py |
| test_service_separation_is_correct_but_validator_assumes_monolith | PASS passed | 0.132s | test_golden_path_validation_staging_current.py |
| test_staging_environment_service_architecture | FAIL failed | 0.000s | test_golden_path_validation_staging_current.py |
| test_recommended_validator_architecture_for_staging | FAIL failed | 0.000s | test_golden_path_validation_staging_current.py |

## Failed Tests Details

### FAILED: test_golden_path_validator_fails_despite_working_services
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_validation_staging_current.py
- **Duration:** 0.001s
- **Error:** tests/e2e/staging/test_golden_path_validation_staging_current.py:162: in test_golden_path_validator_fails_despite_working_services
    assert result.overall_success is False, (
E   AssertionError: ARCHITECTURAL FLAW EXPOSED IN STAGING: Golden Path Validator fails because it looks for auth tables (user_sessions) in backend database. In proper microservice setup, auth tables are in auth service database. This failure is architectural, not functional.
E   assert True is False
E    +  where True = <...

### FAILED: test_validator_prevents_successful_staging_deployment
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_validation_staging_current.py
- **Duration:** 0.348s
- **Error:** tests/e2e/staging/test_golden_path_validation_staging_current.py:253: in test_validator_prevents_successful_staging_deployment
    assert business_impact['validator_blocks_deployment'] is False, (
E   AssertionError: BUSINESS IMPACT: {'validator_blocks_deployment': True, 'services_actually_work': True, 'root_cause': 'architectural_assumptions_in_validator', 'impact': 'prevents_staging_deployments'}. Validator architectural issues are blocking deployments of working services.
E   assert True is F...

### FAILED: test_staging_environment_service_architecture
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_validation_staging_current.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_golden_path_validation_staging_current.py:381: in test_staging_environment_service_architecture
    assert validator_assumptions['conflicts_with_staging_reality'] is False, (
E   AssertionError: STAGING REALITY vs VALIDATOR ASSUMPTIONS: Staging: {'auth_service': {'has_own_database': True, 'contains_tables': ['users', 'user_sessions', 'oauth_credentials'], 'accessible_from': ['auth_service_only']}, 'backend_service': {'has_own_database': True, 'contains_tables': ['chat_thre...

### FAILED: test_recommended_validator_architecture_for_staging
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_validation_staging_current.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_golden_path_validation_staging_current.py:410: in test_recommended_validator_architecture_for_staging
    assert False, (
E   AssertionError: RECOMMENDED STAGING VALIDATOR ARCHITECTURE: {'auth_validation': {'method': 'HTTP call to auth service /health endpoint', 'validates': ['auth service availability', 'JWT capabilities'], 'database_access': 'none_from_backend'}, 'backend_validation': {'method': 'check backend database and components', 'validates': ['backend tables', 'ag...

## Pytest Output Format

```
test_golden_path_validation_staging_current.py::test_auth_service_actually_works_in_staging SKIPPED
test_golden_path_validation_staging_current.py::test_backend_service_actually_works_in_staging SKIPPED
test_golden_path_validation_staging_current.py::test_golden_path_validator_fails_despite_working_services FAILED
test_golden_path_validation_staging_current.py::test_validator_prevents_successful_staging_deployment FAILED
test_golden_path_validation_staging_current.py::test_service_separation_is_correct_but_validator_assumes_monolith PASSED
test_golden_path_validation_staging_current.py::test_staging_environment_service_architecture FAILED
test_golden_path_validation_staging_current.py::test_recommended_validator_architecture_for_staging FAILED

==================================================
1 passed, 4 failed, 2 skipped in 0.65s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Authentication | 1 | 0 | 0 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
