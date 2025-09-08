# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 20:31:35
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 22 (88.0%)
- **Failed:** 3 (12.0%)
- **Skipped:** 0
- **Duration:** 42.40 seconds
- **Pass Rate:** 88.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | FAIL failed | 2.570s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 0.448s | test_priority1_critical.py |
| test_003_websocket_message_send_real | FAIL failed | 0.458s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 1.782s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.378s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.696s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.660s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.786s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.663s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.768s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 2.057s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 1.081s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 1.087s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.693s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 1.044s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.440s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 6.430s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.539s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.815s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 6.070s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.090s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 0.926s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 0.803s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.407s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 0.780s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_001_websocket_connection_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 2.570s
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
- **Duration:** 0.448s
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
- **Duration:** 0.458s
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
22 passed, 3 failed in 42.40s
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
