# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-15 13:10:06
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 7
- **Passed:** 1 (14.3%)
- **Failed:** 6 (85.7%)
- **Skipped:** 0
- **Duration:** 25.19 seconds
- **Pass Rate:** 14.3%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_auth_service_health_comprehensive | PASS passed | 0.601s | test_staging_authentication_service_health.py |
| test_staging_auth_service_e2e_authentication_flow | FAIL failed | 0.290s | test_staging_authentication_service_health.py |
| test_staging_backend_api_service_health | FAIL failed | 6.291s | test_staging_authentication_service_health.py |
| test_staging_websocket_service_basic_connectivity | FAIL failed | 0.009s | test_staging_authentication_service_health.py |
| test_staging_websocket_authenticated_connection | FAIL failed | 0.313s | test_staging_authentication_service_health.py |
| test_staging_service_dependencies_integration | FAIL failed | 15.830s | test_staging_authentication_service_health.py |
| test_staging_environment_readiness_summary | FAIL failed | 0.685s | test_staging_authentication_service_health.py |

## Failed Tests Details

### FAILED: test_staging_auth_service_e2e_authentication_flow
- **File:** C:\netra-apex\tests\e2e\staging\test_staging_authentication_service_health.py
- **Duration:** 0.290s
- **Error:** tests\e2e\staging\test_staging_authentication_service_health.py:175: in test_staging_auth_service_e2e_authentication_flow
    self.assertEqual(
test_framework\ssot\base_test_case.py:610: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401:
E   Response: {"detail":"E2E bypass key required"}
E   This completely blocks Golden Path user authentication.

During handling of the above exce...

### FAILED: test_staging_backend_api_service_health
- **File:** C:\netra-apex\tests\e2e\staging\test_staging_authentication_service_health.py
- **Duration:** 6.291s
- **Error:** tests\e2e\staging\test_staging_authentication_service_health.py:289: in test_staging_backend_api_service_health
    self.assertLessEqual(
test_framework\ssot\base_test_case.py:646: in assertLessEqual
    assert first <= second, msg or f"Expected {first} <= {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Backend service too slow: 6.28s > 5.0s

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_staging_authentication_service_health.py:296: in test_s...

### FAILED: test_staging_websocket_service_basic_connectivity
- **File:** C:\netra-apex\tests\e2e\staging\test_staging_authentication_service_health.py
- **Duration:** 0.009s
- **Error:** tests\e2e\staging\test_staging_authentication_service_health.py:326: in test_staging_websocket_service_basic_connectivity
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:541: in __await_impl__
    self.connection = await self.create_connection()
                      ...

### FAILED: test_staging_websocket_authenticated_connection
- **File:** C:\netra-apex\tests\e2e\staging\test_staging_authentication_service_health.py
- **Duration:** 0.313s
- **Error:** tests\e2e\staging\test_staging_authentication_service_health.py:401: in test_staging_websocket_authenticated_connection
    self.assertEqual(auth_response.status_code, 200, "Authentication failed")
test_framework\ssot\base_test_case.py:610: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_staging_authenti...

### FAILED: test_staging_service_dependencies_integration
- **File:** C:\netra-apex\tests\e2e\staging\test_staging_authentication_service_health.py
- **Duration:** 15.830s
- **Error:** C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\httpx\_transports\default.py:101: in map_httpcore_exceptions
    yield
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\httpx\_transports\default.py:394: in handle_async_request
    resp = await self._pool.handle_async_request(req)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\httpcore\_async\connection_pool.py:256: in handle_async_request
    raise exc...

### FAILED: test_staging_environment_readiness_summary
- **File:** C:\netra-apex\tests\e2e\staging\test_staging_authentication_service_health.py
- **Duration:** 0.685s
- **Error:** tests\e2e\staging\test_staging_authentication_service_health.py:175: in test_staging_auth_service_e2e_authentication_flow
    self.assertEqual(
test_framework\ssot\base_test_case.py:610: in assertEqual
    assert first == second, msg or f"Expected {first} == {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: Authentication failed with status 401:
E   Response: {"detail":"E2E bypass key required"}
E   This completely blocks Golden Path user authentication.

During handling of the above exce...

## Pytest Output Format

```
test_staging_authentication_service_health.py::test_staging_auth_service_health_comprehensive PASSED
test_staging_authentication_service_health.py::test_staging_auth_service_e2e_authentication_flow FAILED
test_staging_authentication_service_health.py::test_staging_backend_api_service_health FAILED
test_staging_authentication_service_health.py::test_staging_websocket_service_basic_connectivity FAILED
test_staging_authentication_service_health.py::test_staging_websocket_authenticated_connection FAILED
test_staging_authentication_service_health.py::test_staging_service_dependencies_integration FAILED
test_staging_authentication_service_health.py::test_staging_environment_readiness_summary FAILED

==================================================
1 passed, 6 failed in 25.19s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 2 | 0 | 2 | 0.0% |
| Authentication | 3 | 1 | 2 | 33.3% |

---
*Report generated by pytest-staging framework v1.0*
