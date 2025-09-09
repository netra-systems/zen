# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-09 12:05:18
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 23 (92.0%)
- **Failed:** 2 (8.0%)
- **Skipped:** 0
- **Duration:** 211.07 seconds
- **Pass Rate:** 92.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | FAIL failed | 0.820s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 4.299s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 3.639s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 4.191s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 4.084s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.588s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.526s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.503s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.523s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.659s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.686s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 0.817s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 0.887s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.707s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 0.889s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.464s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 3.271s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.470s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.744s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 4.386s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 1.710s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 1.174s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 90.890s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 10.880s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 66.975s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_001_websocket_connection_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 0.820s
- **Error:** tests/e2e/staging/test_priority1_critical.py:89: in test_001_websocket_connection_real
    welcome_response = await asyncio.wait_for(ws.recv(), timeout=30)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew/Cellar/python@3.12/3.12.3/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/tasks.py:520: in wait_for
    return await fut
           ^^^^^^^^^
.venv/lib/python3.12/site-packages/websockets/asyncio/connection.py:322: in recv
    raise self.protoc...

### FAILED: test_002_websocket_authentication_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 4.299s
- **Error:** tests/e2e/staging/test_priority1_critical.py:204: in test_002_websocket_authentication_real
    welcome_response = await asyncio.wait_for(ws.recv(), timeout=10)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew/Cellar/python@3.12/3.12.3/Frameworks/Python.framework/Versions/3.12/lib/python3.12/asyncio/tasks.py:520: in wait_for
    return await fut
           ^^^^^^^^^
.venv/lib/python3.12/site-packages/websockets/asyncio/connection.py:322: in recv
    raise self.p...

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
23 passed, 2 failed in 211.07s
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
