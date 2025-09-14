# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-13 18:59:29
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 6
- **Passed:** 1 (16.7%)
- **Failed:** 5 (83.3%)
- **Skipped:** 0
- **Duration:** 0.37 seconds
- **Pass Rate:** 16.7%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_websocket_connection_establishment | FAIL failed | 0.007s | test_websocket_infrastructure_validation_staging.py |
| test_staging_websocket_agent_event_flow | FAIL failed | 0.000s | test_websocket_infrastructure_validation_staging.py |
| test_staging_websocket_concurrent_connections | FAIL failed | 0.001s | test_websocket_infrastructure_validation_staging.py |
| test_staging_websocket_error_handling | FAIL failed | 0.000s | test_websocket_infrastructure_validation_staging.py |
| test_staging_infrastructure_vs_local_docker_comparison | PASS passed | 0.000s | test_websocket_infrastructure_validation_staging.py |
| test_staging_websocket_infrastructure_health_check | FAIL failed | 0.149s | test_websocket_infrastructure_validation_staging.py |

## Failed Tests Details

### FAILED: test_staging_websocket_connection_establishment
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_websocket_infrastructure_validation_staging.py
- **Duration:** 0.007s
- **Error:** tests/e2e/staging/test_websocket_infrastructure_validation_staging.py:69: in test_staging_websocket_connection_establishment
    async with websockets.connect(
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:541: in __await_impl__
    self.connection = await self.create_connection()
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt...

### FAILED: test_staging_websocket_agent_event_flow
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_websocket_infrastructure_validation_staging.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_websocket_infrastructure_validation_staging.py:140: in test_staging_websocket_agent_event_flow
    async with websockets.connect(
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:541: in __await_impl__
    self.connection = await self.create_connection()
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebr...

### FAILED: test_staging_websocket_concurrent_connections
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_websocket_infrastructure_validation_staging.py
- **Duration:** 0.001s
- **Error:** tests/e2e/staging/test_websocket_infrastructure_validation_staging.py:270: in test_staging_websocket_concurrent_connections
    pytest.fail(
E   Failed: Staging concurrent WebSocket connection test failed. Success rate: 0.0% (0/5). Failed connections: 5, Exceptions: 0. This indicates WebSocket infrastructure issues that could impact multi-user chat functionality for enterprise customers....

### FAILED: test_staging_websocket_error_handling
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_websocket_infrastructure_validation_staging.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_websocket_infrastructure_validation_staging.py:301: in test_staging_websocket_error_handling
    async with websockets.connect(
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:541: in __await_impl__
    self.connection = await self.create_connection()
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew...

### FAILED: test_staging_websocket_infrastructure_health_check
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_websocket_infrastructure_validation_staging.py
- **Duration:** 0.149s
- **Error:** tests/e2e/staging/test_websocket_infrastructure_validation_staging.py:432: in test_staging_websocket_infrastructure_health_check
    async with websockets.connect(websocket_endpoint, open_timeout=30.0) as websocket:
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:543:...

## Pytest Output Format

```
test_websocket_infrastructure_validation_staging.py::test_staging_websocket_connection_establishment FAILED
test_websocket_infrastructure_validation_staging.py::test_staging_websocket_agent_event_flow FAILED
test_websocket_infrastructure_validation_staging.py::test_staging_websocket_concurrent_connections FAILED
test_websocket_infrastructure_validation_staging.py::test_staging_websocket_error_handling FAILED
test_websocket_infrastructure_validation_staging.py::test_staging_infrastructure_vs_local_docker_comparison PASSED
test_websocket_infrastructure_validation_staging.py::test_staging_websocket_infrastructure_health_check FAILED

==================================================
1 passed, 5 failed in 0.37s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 5 | 0 | 5 | 0.0% |
| Agent | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
