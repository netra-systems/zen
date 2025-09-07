# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 16:36:55
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 24 (96.0%)
- **Failed:** 1 (4.0%)
- **Skipped:** 0
- **Duration:** 78.87 seconds
- **Pass Rate:** 96.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | PASS passed | 8.779s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 1.654s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 0.973s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 3.977s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 1.239s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 1.633s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 1.370s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 1.021s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 1.443s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 1.211s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 2.112s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 1.382s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 1.651s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 1.144s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 1.879s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.832s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 15.430s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.995s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 1.495s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 10.643s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.972s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 1.492s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 1.467s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.950s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 1.255s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_002_websocket_authentication_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 1.654s
- **Error:** tests\e2e\staging\test_priority1_critical.py:136: in test_002_websocket_authentication_real
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyn...

## Pytest Output Format

```
test_priority1_critical.py::test_001_websocket_connection_real PASSED
test_priority1_critical.py::test_002_websocket_authentication_real FAILED
test_priority1_critical.py::test_003_websocket_message_send_real PASSED
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
24 passed, 1 failed in 78.87s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 3 | 1 | 75.0% |
| Agent | 7 | 7 | 0 | 100.0% |
| Authentication | 1 | 0 | 1 | 0.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
