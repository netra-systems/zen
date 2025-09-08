# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 17:43:36
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 23 (92.0%)
- **Failed:** 2 (8.0%)
- **Skipped:** 0
- **Duration:** 66.22 seconds
- **Pass Rate:** 92.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | FAIL failed | 3.941s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 1.397s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 0.802s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 4.329s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.653s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.980s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.994s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 1.058s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 1.069s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 1.215s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 2.408s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 1.298s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 1.471s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 1.047s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 1.955s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 2.013s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 14.561s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 5.032s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 1.022s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 8.482s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.648s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 1.229s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 1.143s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.900s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 0.967s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_001_websocket_connection_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 3.941s
- **Error:** tests\e2e\staging\test_priority1_critical.py:103: in test_001_websocket_connection_real
    assert got_auth_error, "WebSocket must enforce authentication"
E   AssertionError: WebSocket must enforce authentication
E   assert False...

### FAILED: test_002_websocket_authentication_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 1.397s
- **Error:** tests\e2e\staging\test_priority1_critical.py:160: in test_002_websocket_authentication_real
    assert auth_enforced, "WebSocket should enforce authentication"
E   AssertionError: WebSocket should enforce authentication
E   assert False...

## Pytest Output Format

```
test_priority1_critical.py::test_001_websocket_connection_real FAILED
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
23 passed, 2 failed in 66.22s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 2 | 2 | 50.0% |
| Agent | 7 | 7 | 0 | 100.0% |
| Authentication | 1 | 0 | 1 | 0.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
