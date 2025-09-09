# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-09 16:19:58
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 22 (88.0%)
- **Failed:** 3 (12.0%)
- **Skipped:** 0
- **Duration:** 267.17 seconds
- **Pass Rate:** 88.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | FAIL failed | 0.749s | test_priority1_critical.py |
| test_002_websocket_authentication_real | PASS passed | 0.860s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 0.309s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 0.350s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.247s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.515s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.469s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.470s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.510s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.516s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.372s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 0.645s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 0.803s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.471s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 0.735s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.324s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 2.557s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.357s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.613s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 4.311s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 1.655s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 0.801s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | FAIL failed | 120.014s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.164s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | FAIL failed | 120.004s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_001_websocket_connection_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 0.749s
- **Error:** tests/e2e/staging/test_priority1_critical.py:89: in test_001_websocket_connection_real
    welcome_response = await asyncio.wait_for(ws.recv(), timeout=30)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/websockets/asyncio/connection.py:322: in recv
    raise sel...

### FAILED: test_023_streaming_partial_results_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 120.014s
- **Error:** /opt/homebrew/lib/python3.13/site-packages/pytest_asyncio/plugin.py:426: in runtest
    super().runtest()
/opt/homebrew/lib/python3.13/site-packages/pytest_asyncio/plugin.py:642: in inner
    _loop.run_until_complete(task)
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/base_events.py:712: in run_until_complete
    self.run_forever()
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/ba...

### FAILED: test_025_critical_event_delivery_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 120.004s
- **Error:** /opt/homebrew/lib/python3.13/site-packages/pytest_asyncio/plugin.py:426: in runtest
    super().runtest()
/opt/homebrew/lib/python3.13/site-packages/pytest_asyncio/plugin.py:642: in inner
    _loop.run_until_complete(task)
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/base_events.py:712: in run_until_complete
    self.run_forever()
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/ba...

## Pytest Output Format

```
test_priority1_critical.py::test_001_websocket_connection_real FAILED
test_priority1_critical.py::test_002_websocket_authentication_real PASSED
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
test_priority1_critical.py::test_023_streaming_partial_results_real FAILED
test_priority1_critical.py::test_024_message_ordering_real PASSED
test_priority1_critical.py::test_025_critical_event_delivery_real FAILED

==================================================
22 passed, 3 failed in 267.17s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 3 | 1 | 75.0% |
| Agent | 7 | 7 | 0 | 100.0% |
| Authentication | 1 | 1 | 0 | 100.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
