# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 07:02:41
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 23 (92.0%)
- **Failed:** 2 (8.0%)
- **Skipped:** 0
- **Duration:** 37.49 seconds
- **Pass Rate:** 92.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | PASS passed | 1.686s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 0.912s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 0.402s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 1.190s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.305s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.592s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | FAIL failed | 0.431s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.559s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.962s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.727s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.692s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 0.837s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 1.009s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.564s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 0.961s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.355s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 4.490s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.280s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.838s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 6.177s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.046s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 0.990s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 0.827s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.390s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 0.728s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_002_websocket_authentication_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.912s
- **Error:** E   websockets.exceptions.InvalidStatus: server rejected WebSocket connection: HTTP 403...

### FAILED: test_007_agent_execution_endpoints_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.431s
- **Error:** E   AssertionError: ❌ POST /api/chat: Endpoint not found (404) - TEST FAILURE...

## Pytest Output Format

```
test_priority1_critical.py::test_001_websocket_connection_real PASSED
test_priority1_critical.py::test_002_websocket_authentication_real FAILED
test_priority1_critical.py::test_003_websocket_message_send_real PASSED
test_priority1_critical.py::test_004_websocket_concurrent_connections_real PASSED
test_priority1_critical.py::test_005_agent_discovery_real PASSED
test_priority1_critical.py::test_006_agent_configuration_real PASSED
test_priority1_critical.py::test_007_agent_execution_endpoints_real FAILED
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
23 passed, 2 failed in 37.49s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 3 | 1 | 75.0% |
| Agent | 7 | 6 | 1 | 85.7% |
| Authentication | 1 | 0 | 1 | 0.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
