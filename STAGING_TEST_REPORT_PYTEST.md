# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-15 09:41:08
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 6
- **Passed:** 1 (16.7%)
- **Failed:** 5 (83.3%)
- **Skipped:** 0
- **Duration:** 69.09 seconds
- **Pass Rate:** 16.7%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_health_endpoint_redis_status_failure | FAIL failed | 6.124s | test_redis_golden_path_validation.py |
| test_staging_websocket_connection_redis_dependency_failure | FAIL failed | 10.040s | test_redis_golden_path_validation.py |
| test_staging_session_management_redis_failure | PASS passed | 0.164s | test_redis_golden_path_validation.py |
| test_staging_full_golden_path_redis_impact | FAIL failed | 15.837s | test_redis_golden_path_validation.py |
| test_staging_redis_configuration_diagnosis | FAIL failed | 20.965s | test_redis_golden_path_validation.py |
| test_staging_service_dependencies_redis_cascade_failure | FAIL failed | 15.377s | test_redis_golden_path_validation.py |

## Failed Tests Details

### FAILED: test_staging_health_endpoint_redis_status_failure
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_redis_golden_path_validation.py
- **Duration:** 6.124s
- **Error:** tests\e2e\staging\test_redis_golden_path_validation.py:58: in test_staging_health_endpoint_redis_status_failure
    pytest.fail(f"Health endpoint not accessible: {response.status}")
E   Failed: Health endpoint not accessible: 503...

### FAILED: test_staging_websocket_connection_redis_dependency_failure
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_redis_golden_path_validation.py
- **Duration:** 10.040s
- **Error:** tests\e2e\staging\test_redis_golden_path_validation.py:113: in test_staging_websocket_connection_redis_dependency_failure
    pytest.fail(f"WebSocket endpoint not accessible, possibly due to Redis config issue (Issue #1177): {websocket_error}")
E   Failed: WebSocket endpoint not accessible, possibly due to Redis config issue (Issue #1177):...

### FAILED: test_staging_full_golden_path_redis_impact
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_redis_golden_path_validation.py
- **Duration:** 15.837s
- **Error:** C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\aiohttp\client_reqrep.py:532: in start
    message, payload = await protocol.read()  # type: ignore[union-attr]
                       ^^^^^^^^^^^^^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\aiohttp\streams.py:672: in read
    await self._waiter
E   asyncio.exceptions.CancelledError

The above exception was the direct cause of the following exception:
tests\e2e\staging\test_redis_golden_path_validation.py:177...

### FAILED: test_staging_redis_configuration_diagnosis
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_redis_golden_path_validation.py
- **Duration:** 20.965s
- **Error:** C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\aiohttp\client_reqrep.py:532: in start
    message, payload = await protocol.read()  # type: ignore[union-attr]
                       ^^^^^^^^^^^^^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\aiohttp\streams.py:672: in read
    await self._waiter
E   asyncio.exceptions.CancelledError

The above exception was the direct cause of the following exception:
tests\e2e\staging\test_redis_golden_path_validation.py:211...

### FAILED: test_staging_service_dependencies_redis_cascade_failure
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_redis_golden_path_validation.py
- **Duration:** 15.377s
- **Error:** tests\e2e\staging\test_redis_golden_path_validation.py:314: in test_staging_service_dependencies_redis_cascade_failure
    pytest.fail(f"EXPECTED CASCADE FAILURE - Redis config issue affecting multiple services (Issue #1177): {cascade_analysis}")
E   Failed: EXPECTED CASCADE FAILURE - Redis config issue affecting multiple services (Issue #1177): {'failed_services': ['backend'], 'services_with_redis_issues': ['backend'], 'full_status': {'backend': {'accessible': False, 'error_status': 503}, 'auth...

## Pytest Output Format

```
test_redis_golden_path_validation.py::test_staging_health_endpoint_redis_status_failure FAILED
test_redis_golden_path_validation.py::test_staging_websocket_connection_redis_dependency_failure FAILED
test_redis_golden_path_validation.py::test_staging_session_management_redis_failure PASSED
test_redis_golden_path_validation.py::test_staging_full_golden_path_redis_impact FAILED
test_redis_golden_path_validation.py::test_staging_redis_configuration_diagnosis FAILED
test_redis_golden_path_validation.py::test_staging_service_dependencies_redis_cascade_failure FAILED

==================================================
1 passed, 5 failed in 69.09s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
