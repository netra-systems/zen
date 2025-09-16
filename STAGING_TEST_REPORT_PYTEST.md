# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-15 18:45:29
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 7
- **Passed:** 0 (0.0%)
- **Failed:** 7 (100.0%)
- **Skipped:** 0
- **Duration:** 15.29 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_golden_path_complete_user_message_to_ai_response_flow | FAIL failed | 0.002s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_error_recovery_and_graceful_degradation | FAIL failed | 0.001s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_multi_user_isolation_validation | FAIL failed | 0.001s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_user_authentication_flow | FAIL failed | 0.001s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_websocket_connection_with_auth | FAIL failed | 0.001s | test_golden_path_end_to_end_staging_validation.py |
| test_golden_path_websocket_event_delivery_under_load | FAIL failed | 0.001s | test_golden_path_end_to_end_staging_validation.py |
| test_staging_environment_health_check | FAIL failed | 0.001s | test_golden_path_end_to_end_staging_validation.py |

## Failed Tests Details

### FAILED: test_golden_path_complete_user_message_to_ai_response_flow
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.002s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

### FAILED: test_golden_path_error_recovery_and_graceful_degradation
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.001s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

### FAILED: test_golden_path_multi_user_isolation_validation
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.001s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

### FAILED: test_golden_path_user_authentication_flow
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.001s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

### FAILED: test_golden_path_websocket_connection_with_auth
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.001s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

### FAILED: test_golden_path_websocket_event_delivery_under_load
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.001s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

### FAILED: test_staging_environment_health_check
- **File:** C:\netra-apex\tests\e2e\staging\test_golden_path_end_to_end_staging_validation.py
- **Duration:** 0.001s
- **Error:** test_framework\ssot\base_test_case.py:1262: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:687: in run_until_complete
    return future.result()
           ^^^^^^^^^^^^^^^
test_framework\ssot\base_test_case.py:1067: in asyncSetUp
    super().setUp()
test_framework\ssot\base_test_case.py:388: in setUp
    loop.run_until_complete(self.asyncSetUp())
C:\Users\antho\miniconda3\Lib\asyncio\base_events.py:663: in run_until_complete
    self....

## Pytest Output Format

```
test_golden_path_end_to_end_staging_validation.py::test_golden_path_complete_user_message_to_ai_response_flow FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_error_recovery_and_graceful_degradation FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_multi_user_isolation_validation FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_user_authentication_flow FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_websocket_connection_with_auth FAILED
test_golden_path_end_to_end_staging_validation.py::test_golden_path_websocket_event_delivery_under_load FAILED
test_golden_path_end_to_end_staging_validation.py::test_staging_environment_health_check FAILED

==================================================
0 passed, 7 failed in 15.29s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 2 | 0 | 2 | 0.0% |
| Authentication | 2 | 0 | 2 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
