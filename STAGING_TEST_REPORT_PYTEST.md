# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 19:43:42
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 22 (88.0%)
- **Failed:** 3 (12.0%)
- **Skipped:** 0
- **Duration:** 37.71 seconds
- **Pass Rate:** 88.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | FAIL failed | 2.174s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 0.408s | test_priority1_critical.py |
| test_003_websocket_message_send_real | FAIL failed | 0.402s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 1.351s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.304s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.748s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.594s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.609s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.571s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.724s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.544s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 0.725s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 0.967s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.636s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 0.987s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.429s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 4.473s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.604s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.795s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 5.695s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.020s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 0.963s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 0.785s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.766s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 0.667s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_001_websocket_connection_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 2.174s
- **Error:** tests\e2e\staging\test_priority1_critical.py:82: in test_001_websocket_connection_real
    welcome_response = await asyncio.wait_for(ws.recv(), timeout=10)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\miniconda3\Lib\asyncio\tasks.py:520: in wait_for
    return await fut
           ^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:322: in recv
    raise self.protocol.close_exc from self.recv_exc
E   websockets...

### FAILED: test_002_websocket_authentication_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.408s
- **Error:** tests\e2e\staging\test_priority1_critical.py:149: in test_002_websocket_authentication_real
    await ws.send(json.dumps({
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:476: in send
    async with self.send_context():
..\..\..\..\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:957: in send_conte...

### FAILED: test_003_websocket_message_send_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.402s
- **Error:** tests\e2e\staging\test_priority1_critical.py:342: in test_003_websocket_message_send_real
    assert message_sent, "Should either send authenticated message or detect auth enforcement"
E   AssertionError: Should either send authenticated message or detect auth enforcement
E   assert False...

## Pytest Output Format

```
test_priority1_critical.py::test_001_websocket_connection_real FAILED
test_priority1_critical.py::test_002_websocket_authentication_real FAILED
test_priority1_critical.py::test_003_websocket_message_send_real FAILED
test_priority1_critical.py::test_004_websocket_concurrent_connections_real PASSED
test_priority1_critical.py::test_005_agent_discovery_real PASSED
test_priority1_critical.py::test_006_agent_configuration_real PASSED
test_priority1_critical.py::test_007_agent_execution_endpoints_real PASSED
test_priority1_critical.py::test_008_agent_streaming_capabilities_real PASSED
test_priority1_critical.py::test_009_agent_status_monitoring_real PASSED
test_priority1_critical.py::test_010_tool_execution_endpoints_real PASSED
test_priority1_critical.py::test_011_agent_performance_real PASSED
test_priority1_critical.py::test_012_message_persistence_real PASSED
test_priority1_critical.py::test_013_thread_creation_real PASSED
test_priority1_critical.py::test_014_thread_switching_real PASSED
test_priority1_critical.py::test_015_thread_history_real PASSED
test_priority1_critical.py::test_016_user_context_isolation_real PASSED
test_priority1_critical.py::test_017_concurrent_users_real PASSED
test_priority1_critical.py::test_018_rate_limiting_real PASSED
test_priority1_critical.py::test_019_error_handling_real PASSED
test_priority1_critical.py::test_020_connection_resilience_real PASSED
test_priority1_critical.py::test_021_session_persistence_real PASSED
test_priority1_critical.py::test_022_agent_lifecycle_management_real PASSED
test_priority1_critical.py::test_023_streaming_partial_results_real PASSED
test_priority1_critical.py::test_024_message_ordering_real PASSED
test_priority1_critical.py::test_025_critical_event_delivery_real PASSED

==================================================
22 passed, 3 failed in 37.71s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 1 | 3 | 25.0% |
| Agent | 7 | 7 | 0 | 100.0% |
| Authentication | 1 | 0 | 1 | 0.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
