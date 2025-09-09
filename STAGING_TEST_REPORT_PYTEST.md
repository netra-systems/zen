# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-09 11:13:43
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 25
- **Passed:** 21 (84.0%)
- **Failed:** 4 (16.0%)
- **Skipped:** 0
- **Duration:** 287.31 seconds
- **Pass Rate:** 84.0%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | FAIL failed | 4.540s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 6.781s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 3.131s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 3.473s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 3.414s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.589s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.547s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.504s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.506s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.589s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.445s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 0.643s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 0.886s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.526s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 1.003s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.143s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 2.925s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.336s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.666s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 4.171s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 1.624s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 0.996s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | FAIL failed | 120.007s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.420s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | FAIL failed | 120.004s | test_priority1_critical.py |

## Failed Tests Details

### FAILED: test_001_websocket_connection_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 4.540s
- **Error:** tests/e2e/staging/test_priority1_critical.py:89: in test_001_websocket_connection_real
    welcome_response = await asyncio.wait_for(ws.recv(), timeout=30)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
.test_venv/lib/python3.13/site-packages/websockets/asyncio/connection.py:322: in recv
    raise self.p...

### FAILED: test_002_websocket_authentication_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 6.781s
- **Error:** tests/e2e/staging/test_priority1_critical.py:204: in test_002_websocket_authentication_real
    welcome_response = await asyncio.wait_for(ws.recv(), timeout=10)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
.test_venv/lib/python3.13/site-packages/websockets/asyncio/connection.py:322: in recv
    raise s...

### FAILED: test_023_streaming_partial_results_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 120.007s
- **Error:** .test_venv/lib/python3.13/site-packages/pytest_asyncio/plugin.py:426: in runtest
    super().runtest()
.test_venv/lib/python3.13/site-packages/pytest_asyncio/plugin.py:642: in inner
    _loop.run_until_complete(task)
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/base_events.py:712: in run_until_complete
    self.run_forever()
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/base_eve...

### FAILED: test_025_critical_event_delivery_real
- **File:** /Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_priority1_critical.py
- **Duration:** 120.004s
- **Error:** .test_venv/lib/python3.13/site-packages/pytest_asyncio/plugin.py:426: in runtest
    super().runtest()
.test_venv/lib/python3.13/site-packages/pytest_asyncio/plugin.py:642: in inner
    _loop.run_until_complete(task)
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/base_events.py:712: in run_until_complete
    self.run_forever()
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/base_eve...

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
test_priority1_critical.py::test_023_streaming_partial_results_real FAILED
test_priority1_critical.py::test_024_message_ordering_real PASSED
test_priority1_critical.py::test_025_critical_event_delivery_real FAILED

==================================================
21 passed, 4 failed in 287.31s
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
