# Staging E2E Test Report - Pytest Results - MERGED

**Generated:** 2025-09-12 05:18:52 (Latest) + 2025-09-11 20:57:33 (Previous)  
**Environment:** Staging  
**Test Framework:** Pytest  

## Executive Summary - COMBINED RESULTS

### Latest Run (2025-09-12 05:18:52)
- **Total Tests:** 4
- **Passed:** 1 (25.0%)
- **Failed:** 3 (75.0%)
- **Skipped:** 0
- **Duration:** 2.04 seconds
- **Pass Rate:** 25.0%

### Previous Run (2025-09-11 20:57:33)
- **Total Tests:** 5
- **Passed:** 2 (40.0%)
- **Failed:** 3 (60.0%)
- **Skipped:** 0
- **Duration:** 2.51 seconds
- **Pass Rate:** 40.0%

## Test Results by Priority

<<<<<<< Updated upstream
### CRITICAL Priority Tests (Latest - 2025-09-12)

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_http_connectivity | PASS passed | 0.706s | test_staging_connectivity_validation.py |
| test_002_websocket_connectivity | FAIL failed | 0.159s | test_staging_connectivity_validation.py |
| test_003_agent_request_pipeline | FAIL failed | 0.156s | test_staging_connectivity_validation.py |
| test_004_generate_connectivity_report | FAIL failed | 0.726s | test_staging_connectivity_validation.py |

### NORMAL Priority Tests (Previous - 2025-09-11)

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_health_check | FAIL failed | 0.486s | test_1_websocket_events_staging.py |
| test_websocket_connection | PASS passed | 0.166s | test_1_websocket_events_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.350s | test_1_websocket_events_staging.py |
| test_websocket_event_flow_real | FAIL failed | 0.134s | test_1_websocket_events_staging.py |
| test_concurrent_websocket_real | FAIL failed | 0.137s | test_1_websocket_events_staging.py |

## Failed Tests Details - Latest Run (2025-09-12)

### FAILED: test_002_websocket_connectivity
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_staging_connectivity_validation.py
- **Duration:** 0.159s
- **Error:** tests\e2e\staging\test_staging_connectivity_validation.py:330: in test_002_websocket_connectivity
    assert result["success"], f"WebSocket connectivity failed: {result.get('error', 'Unknown error')}"
E   AssertionError: WebSocket connectivity failed: server rejected WebSocket connection: HTTP 500
E   assert False...

### FAILED: test_003_agent_request_pipeline
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_staging_connectivity_validation.py
- **Duration:** 0.156s
- **Error:** tests\e2e\staging\test_staging_connectivity_validation.py:345: in test_003_agent_request_pipeline
    assert result["success"], f"Agent pipeline test failed: {result.get('error', 'Unknown error')}"
E   AssertionError: Agent pipeline test failed: server rejected WebSocket connection: HTTP 500
E   assert False...

### FAILED: test_004_generate_connectivity_report
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_staging_connectivity_validation.py
- **Duration:** 0.726s
- **Error:** tests\e2e\staging\test_staging_connectivity_validation.py:409: in test_004_generate_connectivity_report
    assert success_rate >= 100.0, f"All connectivity tests should pass for staging validation"
E   AssertionError: All connectivity tests should pass for staging validation
E   assert 33.33333333333333 >= 100.0...

## Failed Tests Details - Previous Run (2025-09-11)

### FAILED: test_health_check
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_1_websocket_events_staging.py
- **Duration:** 0.486s
- **Error:** tests/e2e/staging_test_base.py:322: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/e2e/staging/test_1_websocket_events_staging.py:54: in test_health_check
    await self.verify_api_health()
tests/e2e/staging_test_base.py:272: in verify_api_health
    assert response.status_code == 200, f"API health check failed with status {response.status_code}"
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AssertionError: API health check failed with status 422...

### FAILED: test_websocket_event_flow_real
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_1_websocket_events_staging.py
- **Duration:** 0.134s
- **Error:** tests/e2e/staging_test_base.py:322: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/e2e/staging/test_1_websocket_events_staging.py:222: in test_websocket_event_flow_real
    async with websockets.connect(
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:543: in __await_impl__
    await self.con...

### FAILED: test_concurrent_websocket_real
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_1_websocket_events_staging.py
- **Duration:** 0.137s
- **Error:** tests/e2e/staging_test_base.py:322: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/e2e/staging/test_1_websocket_events_staging.py:376: in test_concurrent_websocket_real
    results = await asyncio.gather(*tasks)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/e2e/staging/test_1_websocket_events_staging.py:350: in test_connection
    async with websockets.connect(
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/client.py:587: in __aen...

=======
>>>>>>> Stashed changes
## Pytest Output Format

### Latest Run (2025-09-12)
```
test_staging_connectivity_validation.py::test_001_http_connectivity PASSED
test_staging_connectivity_validation.py::test_002_websocket_connectivity FAILED
test_staging_connectivity_validation.py::test_003_agent_request_pipeline FAILED
test_staging_connectivity_validation.py::test_004_generate_connectivity_report FAILED

==================================================
1 passed, 3 failed in 2.04s
```

### Previous Run (2025-09-11)
```

==================================================
0 passed, 0 failed in 0.38s
```

## Test Coverage Matrix - Combined Analysis

### Latest Run Coverage (2025-09-12)
| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 0 | 1 | 0.0% |
| Agent | 1 | 0 | 1 | 0.0% |

### Previous Run Coverage (2025-09-11)
| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|

---
*Report generated by pytest-staging framework v1.0*
