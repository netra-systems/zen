# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-12 20:11:36
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 10
- **Passed:** 6 (60.0%)
- **Failed:** 4 (40.0%)
- **Skipped:** 0
- **Duration:** 0.44 seconds
- **Pass Rate:** 60.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_websocket_connection_availability | FAIL failed | 0.017s | test_websocket_service_staging_validation.py |
| test_staging_websocket_authentication_flow | PASS passed | 0.008s | test_websocket_service_staging_validation.py |
| test_staging_websocket_message_routing | FAIL failed | 0.007s | test_websocket_service_staging_validation.py |
| test_staging_websocket_error_handling | PASS passed | 0.000s | test_websocket_service_staging_validation.py |
| test_staging_websocket_performance_baseline | PASS passed | 0.011s | test_websocket_service_staging_validation.py |
| test_staging_websocket_configuration_validation | FAIL failed | 0.000s | test_websocket_service_staging_validation.py |
| test_staging_websocket_business_value_indicators | PASS passed | 0.000s | test_websocket_service_staging_validation.py |
| test_staging_websocket_golden_path_simulation | FAIL failed | 0.000s | test_websocket_service_staging_validation.py |
| test_staging_websocket_fallback_strategy | PASS passed | 0.000s | test_websocket_service_staging_validation.py |
| test_staging_websocket_development_velocity_impact | PASS passed | 0.000s | test_websocket_service_staging_validation.py |

## Failed Tests Details

### FAILED: test_staging_websocket_connection_availability
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_websocket_service_staging_validation.py
- **Duration:** 0.017s
- **Error:** tests\e2e\staging\test_websocket_service_staging_validation.py:86: in test_staging_websocket_connection_availability
    self.config.WEBSOCKET_URL,
    ^^^^^^^^^^^
E   AttributeError: 'TestWebSocketServiceStagingValidation' object has no attribute 'config'

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_websocket_service_staging_validation.py:105: in test_staging_websocket_connection_availability
    self.fail(f"Staging WebSocket connection failed: {st...

### FAILED: test_staging_websocket_message_routing
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_websocket_service_staging_validation.py
- **Duration:** 0.007s
- **Error:** tests\e2e\staging\test_websocket_service_staging_validation.py:187: in test_staging_websocket_message_routing
    self.config.WEBSOCKET_URL,
    ^^^^^^^^^^^
E   AttributeError: 'TestWebSocketServiceStagingValidation' object has no attribute 'config'

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_websocket_service_staging_validation.py:215: in test_staging_websocket_message_routing
    self.fail(f"Unexpected error in message routing: {e}")
    ^^^^^^^^...

### FAILED: test_staging_websocket_configuration_validation
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_websocket_service_staging_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_websocket_service_staging_validation.py:334: in test_staging_websocket_configuration_validation
    self.assertTrue(self.config.WEBSOCKET_URL.startswith("wss://"),
                    ^^^^^^^^^^^
E   AttributeError: 'TestWebSocketServiceStagingValidation' object has no attribute 'config'...

### FAILED: test_staging_websocket_golden_path_simulation
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_websocket_service_staging_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_websocket_service_staging_validation.py:441: in test_staging_websocket_golden_path_simulation
    self.assertIn("connection", step.lower(),
test_framework\ssot\base_test_case.py:544: in assertIn
    assert member in container, msg or f"Expected {member} in {container}"
           ^^^^^^^^^^^^^^^^^^^
E   AssertionError: WebSocket steps should mention connection...

## Pytest Output Format

```
test_websocket_service_staging_validation.py::test_staging_websocket_connection_availability FAILED
test_websocket_service_staging_validation.py::test_staging_websocket_authentication_flow PASSED
test_websocket_service_staging_validation.py::test_staging_websocket_message_routing FAILED
test_websocket_service_staging_validation.py::test_staging_websocket_error_handling PASSED
test_websocket_service_staging_validation.py::test_staging_websocket_performance_baseline PASSED
test_websocket_service_staging_validation.py::test_staging_websocket_configuration_validation FAILED
test_websocket_service_staging_validation.py::test_staging_websocket_business_value_indicators PASSED
test_websocket_service_staging_validation.py::test_staging_websocket_golden_path_simulation FAILED
test_websocket_service_staging_validation.py::test_staging_websocket_fallback_strategy PASSED
test_websocket_service_staging_validation.py::test_staging_websocket_development_velocity_impact PASSED

==================================================
6 passed, 4 failed in 0.44s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 10 | 6 | 4 | 60.0% |
| Authentication | 1 | 1 | 0 | 100.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
