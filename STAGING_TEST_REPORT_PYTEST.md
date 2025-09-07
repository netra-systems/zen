# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 08:23:54
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 16
- **Passed:** 10 (62.5%)
- **Failed:** 6 (37.5%)
- **Skipped:** 0
- **Duration:** 21.18 seconds
- **Pass Rate:** 62.5%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_health_check | PASS passed | 0.424s | test_1_websocket_events_staging.py |
| test_websocket_connection | FAIL failed | 0.369s | test_1_websocket_events_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.532s | test_1_websocket_events_staging.py |
| test_websocket_event_flow_real | FAIL failed | 0.376s | test_1_websocket_events_staging.py |
| test_concurrent_websocket_real | FAIL failed | 1.554s | test_1_websocket_events_staging.py |
| test_message_endpoints | PASS passed | 0.432s | test_2_message_flow_staging.py |
| test_real_message_api_endpoints | PASS passed | 0.688s | test_2_message_flow_staging.py |
| test_real_websocket_message_flow | PASS passed | 0.343s | test_2_message_flow_staging.py |
| test_real_thread_management | PASS passed | 0.528s | test_2_message_flow_staging.py |
| test_real_error_handling_flow | PASS passed | 1.086s | test_2_message_flow_staging.py |
| test_real_agent_discovery | PASS passed | 0.781s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.601s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | FAIL failed | 0.339s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | FAIL failed | 1.093s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | FAIL failed | 1.023s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 3.412s | test_3_agent_pipeline_staging.py |

## Failed Tests Details

### FAILED: test_websocket_connection
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.369s
- **Error:** tests\e2e\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_1_websocket_events_staging.py:73: in test_websocket_connection
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await...

### FAILED: test_websocket_event_flow_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.376s
- **Error:** tests\e2e\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_1_websocket_events_staging.py:139: in test_websocket_event_flow_real
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in _...

### FAILED: test_concurrent_websocket_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 1.554s
- **Error:** tests\e2e\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_1_websocket_events_staging.py:247: in test_concurrent_websocket_real
    results = await asyncio.gather(*tasks)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_1_websocket_events_staging.py:221: in test_connection
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client....

### FAILED: test_real_agent_pipeline_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 0.339s
- **Error:** tests\e2e\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_3_agent_pipeline_staging.py:204: in test_real_agent_pipeline_execution
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in...

### FAILED: test_real_agent_lifecycle_monitoring
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 1.093s
- **Error:** tests\e2e\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_3_agent_pipeline_staging.py:357: in test_real_agent_lifecycle_monitoring
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: ...

### FAILED: test_real_pipeline_error_handling
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 1.023s
- **Error:** tests\e2e\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_3_agent_pipeline_staging.py:450: in test_real_pipeline_error_handling
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in ...

## Pytest Output Format

```
test_1_websocket_events_staging.py::test_health_check PASSED
test_1_websocket_events_staging.py::test_websocket_connection FAILED
test_1_websocket_events_staging.py::test_api_endpoints_for_agents PASSED
test_1_websocket_events_staging.py::test_websocket_event_flow_real FAILED
test_1_websocket_events_staging.py::test_concurrent_websocket_real FAILED
test_2_message_flow_staging.py::test_message_endpoints PASSED
test_2_message_flow_staging.py::test_real_message_api_endpoints PASSED
test_2_message_flow_staging.py::test_real_websocket_message_flow PASSED
test_2_message_flow_staging.py::test_real_thread_management PASSED
test_2_message_flow_staging.py::test_real_error_handling_flow PASSED
test_3_agent_pipeline_staging.py::test_real_agent_discovery PASSED
test_3_agent_pipeline_staging.py::test_real_agent_configuration PASSED
test_3_agent_pipeline_staging.py::test_real_agent_pipeline_execution FAILED
test_3_agent_pipeline_staging.py::test_real_agent_lifecycle_monitoring FAILED
test_3_agent_pipeline_staging.py::test_real_pipeline_error_handling FAILED
test_3_agent_pipeline_staging.py::test_real_pipeline_metrics PASSED

==================================================
10 passed, 6 failed in 21.18s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 1 | 3 | 25.0% |
| Agent | 5 | 3 | 2 | 60.0% |

---
*Report generated by pytest-staging framework v1.0*
