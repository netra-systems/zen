# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-15 18:45:56
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 5
- **Passed:** 0 (0.0%)
- **Failed:** 5 (100.0%)
- **Skipped:** 0
- **Duration:** 14.36 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_gcp_redis_websocket_readiness_assessment | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_1011_error_risk_prediction | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_chat_functionality_readiness | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_production_scalability_readiness | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_monitoring_observability_readiness | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |

## Failed Tests Details

### FAILED: test_gcp_redis_websocket_readiness_assessment
- **File:** C:\netra-apex\tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py:87: in test_gcp_redis_websocket_readiness_assessment
    self.assertTrue(
test_framework\ssot\base_test_case.py:641: in assertTrue
    assert expr, msg or f"Expected True, got {expr}"
           ^^^^
E   AssertionError: CRITICAL: System not ready for GCP deployment:
E     - Overall readiness: False
E     - Redis SSOT score: 25/100
E     - WebSocket stability: 30/100
E     - Integration health: 20/100
E     - Deployment blockers: ['...

### FAILED: test_gcp_redis_websocket_1011_error_risk_prediction
- **File:** C:\netra-apex\tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py:108: in test_gcp_redis_websocket_1011_error_risk_prediction
    self.assertLess(
test_framework\ssot\base_test_case.py:665: in assertLess
    assert first < second, msg or f"Expected {first} < {second}"
           ^^^^^^^^^^^^^^
E   AssertionError: CRITICAL: High WebSocket 1011 error probability in GCP:
E     - Error probability: 85%
E     - Risk factors: ['Multiple Redis managers causing connection conflicts', 'Connection pool fra...

### FAILED: test_gcp_redis_websocket_chat_functionality_readiness
- **File:** C:\netra-apex\tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py:129: in test_gcp_redis_websocket_chat_functionality_readiness
    self.assertTrue(
test_framework\ssot\base_test_case.py:641: in assertTrue
    assert expr, msg or f"Expected True, got {expr}"
           ^^^^
E   AssertionError: CRITICAL: Chat functionality not ready for GCP production:
E     - Chat readiness: False
E     - User connection reliability: 65%
E     - Agent execution reliability: 70%
E     - State persistence reliabili...

### FAILED: test_gcp_redis_websocket_production_scalability_readiness
- **File:** C:\netra-apex\tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py:151: in test_gcp_redis_websocket_production_scalability_readiness
    self.assertGreaterEqual(
test_framework\ssot\base_test_case.py:661: in assertGreaterEqual
    assert first >= second, msg or f"Expected {first} >= {second}"
           ^^^^^^^^^^^^^^^
E   AssertionError: CRITICAL: System not ready for production scale:
E     - Scalability score: 35/100
E     - Connection pool efficiency: 25%
E     - Resource utilization: 40%
E   ...

### FAILED: test_gcp_redis_websocket_monitoring_observability_readiness
- **File:** C:\netra-apex\tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_gcp_redis_websocket_golden_path_simple.py:173: in test_gcp_redis_websocket_monitoring_observability_readiness
    self.assertTrue(
test_framework\ssot\base_test_case.py:641: in assertTrue
    assert expr, msg or f"Expected True, got {expr}"
           ^^^^
E   AssertionError: CRITICAL: Monitoring not adequate for GCP production:
E     - Monitoring coverage: 45%
E     - Redis visibility: Poor - Multiple managers obscure metrics
E     - WebSocket tracking: Incomplete - Missi...

## Pytest Output Format

```
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_readiness_assessment FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_1011_error_risk_prediction FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_chat_functionality_readiness FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_production_scalability_readiness FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_monitoring_observability_readiness FAILED

==================================================
0 passed, 5 failed in 14.36s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 5 | 0 | 5 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
