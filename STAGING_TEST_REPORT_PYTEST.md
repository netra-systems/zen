# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-17 03:38:09
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 7
- **Passed:** 0 (0.0%)
- **Failed:** 7 (100.0%)
- **Skipped:** 0
- **Duration:** 31.66 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_environment_health_check | FAIL failed | 30.267s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_user_authentication_flow | FAIL failed | 0.145s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_websocket_connection_with_auth | FAIL failed | 0.142s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_complete_user_message_to_ai_response_flow | FAIL failed | 0.132s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_multi_user_isolation_validation | FAIL failed | 0.140s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_websocket_event_delivery_under_load | FAIL failed | 0.141s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_error_recovery_and_graceful_degradation | FAIL failed | 0.137s | test_golden_path_end_to_end_staging_validation.py |

## Failed Tests Details

### FAILED: test_staging_environment_health_check
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 30.267s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:152: in test_staging_environment_health_check
    self.assertTrue(
test_framework/ssot/base_test_case.py:828: in assertTrue
    assert expr, msg or f"Expected True, got {expr}"
           ^^^^
E   AssertionError: STAGING ENVIRONMENT HEALTH CHECK FAILED:
E   Service Health Status:
E     - Auth Service: {'status_code': 200, 'healthy': True, 'response_time': 1758105457.918472}
E     - Backend API: {'status_code': None, 'healthy': F...

### FAILED: test_golden_path_user_authentication_flow
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.145s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:185: in test_golden_path_user_authentication_flow
    self.assertEqual(
test_framework/ssot/base_test_case.py:820: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401.
E   Response: {"detail":"E2E bypass key required"}
E   This blocks the Golden Path at the authentication step.

During handling of the above exceptio...

### FAILED: test_golden_path_websocket_connection_with_auth
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.142s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:185: in test_golden_path_user_authentication_flow
    self.assertEqual(
test_framework/ssot/base_test_case.py:820: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401.
E   Response: {"detail":"E2E bypass key required"}
E   This blocks the Golden Path at the authentication step.

During handling of the above exceptio...

### FAILED: test_golden_path_complete_user_message_to_ai_response_flow
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.132s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:185: in test_golden_path_user_authentication_flow
    self.assertEqual(
test_framework/ssot/base_test_case.py:820: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401.
E   Response: {"detail":"E2E bypass key required"}
E   This blocks the Golden Path at the authentication step.

During handling of the above exceptio...

### FAILED: test_golden_path_multi_user_isolation_validation
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.140s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:185: in test_golden_path_user_authentication_flow
    self.assertEqual(
test_framework/ssot/base_test_case.py:820: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401.
E   Response: {"detail":"E2E bypass key required"}
E   This blocks the Golden Path at the authentication step.

During handling of the above exceptio...

### FAILED: test_golden_path_websocket_event_delivery_under_load
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.141s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:185: in test_golden_path_user_authentication_flow
    self.assertEqual(
test_framework/ssot/base_test_case.py:820: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401.
E   Response: {"detail":"E2E bypass key required"}
E   This blocks the Golden Path at the authentication step.

During handling of the above exceptio...

### FAILED: test_golden_path_error_recovery_and_graceful_degradation
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.137s
- **Error:** tests/e2e/staging/test_golden_path_end_to_end_staging_validation.py:185: in test_golden_path_user_authentication_flow
    self.assertEqual(
test_framework/ssot/base_test_case.py:820: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401.
E   Response: {"detail":"E2E bypass key required"}
E   This blocks the Golden Path at the authentication step.

During handling of the above exceptio...

## Pytest Output Format

```
test_golden_path_end_to_end_staging_validation.py::test_staging_environment_health_check FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_user_authentication_flow FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_websocket_connection_with_auth FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_complete_user_message_to_ai_response_flow FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_multi_user_isolation_validation FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_websocket_event_delivery_under_load FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_error_recovery_and_graceful_degradation FAILED

==================================================
0 passed, 7 failed in 31.66s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 2 | 0 | 2 | 0.0% |
| Authentication | 2 | 0 | 2 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
