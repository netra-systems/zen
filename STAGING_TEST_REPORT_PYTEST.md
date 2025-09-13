# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-13 15:42:26
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 8
- **Passed:** 0 (0.0%)
- **Failed:** 6 (75.0%)
- **Skipped:** 2
- **Duration:** 2.90 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_complete_golden_path_staging_environment | FAIL failed | 0.370s | test_websocket_ssot_golden_path.py |
| test_websocket_connection_staging_reliability | FAIL failed | 0.286s | test_websocket_ssot_golden_path.py |
| test_ai_agent_response_quality_staging | FAIL failed | 0.220s | test_websocket_ssot_golden_path.py |
| test_multi_user_staging_scenarios | FAIL failed | 0.612s | test_websocket_ssot_golden_path.py |
| test_staging_performance_regression | FAIL failed | 0.213s | test_websocket_ssot_golden_path.py |
| test_staging_deployment_confidence_validation | FAIL failed | 0.215s | test_websocket_ssot_golden_path.py |
| test_concurrent_user_load_staging | SKIP skipped | 0.000s | test_websocket_ssot_golden_path.py |
| test_memory_usage_staging_validation | SKIP skipped | 0.000s | test_websocket_ssot_golden_path.py |

## Failed Tests Details

### FAILED: test_complete_golden_path_staging_environment
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_ssot_golden_path.py
- **Duration:** 0.370s
- **Error:** tests\e2e\staging\test_websocket_ssot_golden_path.py:238: in test_complete_golden_path_staging_environment
    auth_headers = await self._authenticate_staging_user()
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_ssot_golden_path.py:100: in _authenticate_staging_user
    "email": self.test_email,
             ^^^^^^^^^^^^^^^
E   AttributeError: 'TestWebSocketSSoTGoldenPathStaging' object has no attribute 'test_email'...

### FAILED: test_websocket_connection_staging_reliability
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_ssot_golden_path.py
- **Duration:** 0.286s
- **Error:** tests\e2e\staging\test_websocket_ssot_golden_path.py:296: in test_websocket_connection_staging_reliability
    auth_headers = await self._authenticate_staging_user()
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_ssot_golden_path.py:100: in _authenticate_staging_user
    "email": self.test_email,
             ^^^^^^^^^^^^^^^
E   AttributeError: 'TestWebSocketSSoTGoldenPathStaging' object has no attribute 'test_email'...

### FAILED: test_ai_agent_response_quality_staging
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_ssot_golden_path.py
- **Duration:** 0.220s
- **Error:** tests\e2e\staging\test_websocket_ssot_golden_path.py:361: in test_ai_agent_response_quality_staging
    auth_headers = await self._authenticate_staging_user()
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_ssot_golden_path.py:100: in _authenticate_staging_user
    "email": self.test_email,
             ^^^^^^^^^^^^^^^
E   AttributeError: 'TestWebSocketSSoTGoldenPathStaging' object has no attribute 'test_email'...

### FAILED: test_multi_user_staging_scenarios
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_ssot_golden_path.py
- **Duration:** 0.612s
- **Error:** tests\e2e\staging\test_websocket_ssot_golden_path.py:492: in test_multi_user_staging_scenarios
    assert success_rate >= 0.8, \
E   AssertionError: Multi-user success rate too low in staging: 0.00
E   assert 0.0 >= 0.8...

### FAILED: test_staging_performance_regression
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_ssot_golden_path.py
- **Duration:** 0.213s
- **Error:** tests\e2e\staging\test_websocket_ssot_golden_path.py:521: in test_staging_performance_regression
    auth_headers = await self._authenticate_staging_user()
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_websocket_ssot_golden_path.py:100: in _authenticate_staging_user
    "email": self.test_email,
             ^^^^^^^^^^^^^^^
E   AttributeError: 'TestWebSocketSSoTGoldenPathStaging' object has no attribute 'test_email'...

### FAILED: test_staging_deployment_confidence_validation
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_ssot_golden_path.py
- **Duration:** 0.215s
- **Error:** tests\e2e\staging\test_websocket_ssot_golden_path.py:664: in test_staging_deployment_confidence_validation
    assert system_health_score >= 1.0, \
E   AssertionError: System health insufficient for deployment: 0.00 < 1.0
E   assert 0.0 >= 1.0...

## Pytest Output Format

```
test_websocket_ssot_golden_path.py::test_complete_golden_path_staging_environment FAILED
test_websocket_ssot_golden_path.py::test_websocket_connection_staging_reliability FAILED
test_websocket_ssot_golden_path.py::test_ai_agent_response_quality_staging FAILED
test_websocket_ssot_golden_path.py::test_multi_user_staging_scenarios FAILED
test_websocket_ssot_golden_path.py::test_staging_performance_regression FAILED
test_websocket_ssot_golden_path.py::test_staging_deployment_confidence_validation FAILED
test_websocket_ssot_golden_path.py::test_concurrent_user_load_staging SKIPPED
test_websocket_ssot_golden_path.py::test_memory_usage_staging_validation SKIPPED

==================================================
0 passed, 6 failed, 2 skipped in 2.90s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 0 | 1 | 0.0% |
| Agent | 1 | 0 | 1 | 0.0% |
| Performance | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
