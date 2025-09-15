# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-15 05:25:11
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 5
- **Passed:** 0 (0.0%)
- **Failed:** 5 (100.0%)
- **Skipped:** 0
- **Duration:** 2.83 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_all_business_critical_events_delivered_staging | FAIL failed | 0.549s | test_websocket_events_business_critical_staging.py |
| test_websocket_events_proper_sequence_staging | FAIL failed | 0.322s | test_websocket_events_business_critical_staging.py |
| test_websocket_events_content_quality_staging | FAIL failed | 0.319s | test_websocket_events_business_critical_staging.py |
| test_websocket_events_reliability_under_staging_load | FAIL failed | 0.285s | test_websocket_events_business_critical_staging.py |
| test_websocket_events_business_value_metrics | FAIL failed | 0.306s | test_websocket_events_business_critical_staging.py |

## Failed Tests Details

### FAILED: test_all_business_critical_events_delivered_staging
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_events_business_critical_staging.py
- **Duration:** 0.549s
- **Error:** tests\e2e\staging\test_websocket_events_business_critical_staging.py:161: in test_all_business_critical_events_delivered_staging
    auth_token = await self._authenticate_staging_user()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_events_business_critical_staging.py:146: in _authenticate_staging_user
    raise Exception(f"Authentication failed: {auth_response.status_code}")
E   Exception: Authentication failed: 401...

### FAILED: test_websocket_events_proper_sequence_staging
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_events_business_critical_staging.py
- **Duration:** 0.322s
- **Error:** tests\e2e\staging\test_websocket_events_business_critical_staging.py:268: in test_websocket_events_proper_sequence_staging
    auth_token = await self._authenticate_staging_user()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_events_business_critical_staging.py:146: in _authenticate_staging_user
    raise Exception(f"Authentication failed: {auth_response.status_code}")
E   Exception: Authentication failed: 401...

### FAILED: test_websocket_events_content_quality_staging
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_events_business_critical_staging.py
- **Duration:** 0.319s
- **Error:** tests\e2e\staging\test_websocket_events_business_critical_staging.py:357: in test_websocket_events_content_quality_staging
    auth_token = await self._authenticate_staging_user()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_events_business_critical_staging.py:146: in _authenticate_staging_user
    raise Exception(f"Authentication failed: {auth_response.status_code}")
E   Exception: Authentication failed: 401...

### FAILED: test_websocket_events_reliability_under_staging_load
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_events_business_critical_staging.py
- **Duration:** 0.285s
- **Error:** tests\e2e\staging\test_websocket_events_business_critical_staging.py:450: in test_websocket_events_reliability_under_staging_load
    auth_token = await self._authenticate_staging_user()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_events_business_critical_staging.py:146: in _authenticate_staging_user
    raise Exception(f"Authentication failed: {auth_response.status_code}")
E   Exception: Authentication failed: 401...

### FAILED: test_websocket_events_business_value_metrics
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_events_business_critical_staging.py
- **Duration:** 0.306s
- **Error:** tests\e2e\staging\test_websocket_events_business_critical_staging.py:555: in test_websocket_events_business_value_metrics
    auth_token = await self._authenticate_staging_user()
                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_events_business_critical_staging.py:146: in _authenticate_staging_user
    raise Exception(f"Authentication failed: {auth_response.status_code}")
E   Exception: Authentication failed: 401...

## Pytest Output Format

```
test_websocket_events_business_critical_staging.py::test_all_business_critical_events_delivered_staging FAILED
test_websocket_events_business_critical_staging.py::test_websocket_events_proper_sequence_staging FAILED
test_websocket_events_business_critical_staging.py::test_websocket_events_content_quality_staging FAILED
test_websocket_events_business_critical_staging.py::test_websocket_events_reliability_under_staging_load FAILED
test_websocket_events_business_critical_staging.py::test_websocket_events_business_value_metrics FAILED

==================================================
0 passed, 5 failed in 2.83s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 0 | 4 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
