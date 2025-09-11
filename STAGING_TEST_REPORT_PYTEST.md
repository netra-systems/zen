# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-11 10:17:55
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 6
- **Passed:** 0 (0.0%)
- **Failed:** 6 (100.0%)
- **Skipped:** 0
- **Duration:** 2.04 seconds
- **Pass Rate:** 0.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_jwt_secret_consistency_verification | FAIL failed | 0.361s | test_websocket_auth_fix_verification.py |
| test_gcp_redis_websocket_1011_error_risk_prediction | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_chat_functionality_readiness | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_monitoring_observability_readiness | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_production_scalability_readiness | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |
| test_gcp_redis_websocket_readiness_assessment | FAIL failed | 0.000s | test_gcp_redis_websocket_golden_path_simple.py |

## Failed Tests Details

### FAILED: test_jwt_secret_consistency_verification
- **File:** /Users/anthony/Desktop/netra-apex/tests/e2e/staging/test_websocket_auth_fix_verification.py
- **Duration:** 0.361s
- **Error:** tests/e2e/staging_test_base.py:308: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
/Users/anthony/Documents/GitHub/netra-apex/tests/e2e/staging/test_websocket_auth_fix_verification.py:189: in test_jwt_secret_consistency_verification
    ???
/opt/homebrew/Cellar/python@3.13/3.13.7/Frameworks/Python.framework/Versions/3.13/lib/python3.13/asyncio/tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
/opt/homebrew/lib/python3.13/site-packages/w...

### FAILED: test_gcp_redis_websocket_1011_error_risk_prediction
- **File:** /Users/rindhujajohnson/Netra/GitHub/netra-apex/tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py:57: in test_gcp_redis_websocket_1011_error_risk_prediction
    self.assertLess(
E   AssertionError: 85 not less than 25 : CRITICAL: High WebSocket 1011 error probability in GCP:
E     - Error probability: 85%
E     - Risk factors: ['Multiple Redis managers causing connection conflicts', 'Connection pool fragmentation', 'Redis initialization race conditions', 'WebSocket-Redis integration complexity', 'GCP Cloud Run connection limita...

### FAILED: test_gcp_redis_websocket_chat_functionality_readiness
- **File:** /Users/rindhujajohnson/Netra/GitHub/netra-apex/tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py:78: in test_gcp_redis_websocket_chat_functionality_readiness
    self.assertTrue(
E   AssertionError: False is not true : CRITICAL: Chat functionality not ready for GCP production:
E     - Chat readiness: False
E     - User connection reliability: 65%
E     - Agent execution reliability: 70%
E     - State persistence reliability: 50%
E     - End-to-end success rate: 60%
E     - Critical dependencies: ['Unified Redis manager (MISSIN...

### FAILED: test_gcp_redis_websocket_monitoring_observability_readiness
- **File:** /Users/rindhujajohnson/Netra/GitHub/netra-apex/tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py:122: in test_gcp_redis_websocket_monitoring_observability_readiness
    self.assertTrue(
E   AssertionError: False is not true : CRITICAL: Monitoring not adequate for GCP production:
E     - Monitoring coverage: 45%
E     - Redis visibility: Poor - Multiple managers obscure metrics
E     - WebSocket tracking: Incomplete - Missing integration events
E     - Error detection capability: Limited - No Redis correlation
E     - Alert con...

### FAILED: test_gcp_redis_websocket_production_scalability_readiness
- **File:** /Users/rindhujajohnson/Netra/GitHub/netra-apex/tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_gcp_redis_websocket_production_scalability_readiness
    self.assertGreaterEqual(
E   AssertionError: 35 not greater than or equal to 75 : CRITICAL: System not ready for production scale:
E     - Scalability score: 35/100
E     - Connection pool efficiency: 25%
E     - Resource utilization: 40%
E     - Concurrent user capacity: 100
E     - Performance bottlenecks: ['Multiple Redis connection pools', 'Connection manager...

### FAILED: test_gcp_redis_websocket_readiness_assessment
- **File:** /Users/rindhujajohnson/Netra/GitHub/netra-apex/tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py
- **Duration:** 0.000s
- **Error:** tests/e2e/staging/test_gcp_redis_websocket_golden_path_simple.py:36: in test_gcp_redis_websocket_readiness_assessment
    self.assertTrue(
E   AssertionError: False is not true : CRITICAL: System not ready for GCP deployment:
E     - Overall readiness: False
E     - Redis SSOT score: 25/100
E     - WebSocket stability: 30/100
E     - Integration health: 20/100
E     - Deployment blockers: ['12 competing Redis manager classes', 'Multiple Redis connection pools', 'WebSocket 1011 error vulnerabilit...

## Pytest Output Format

```
test_websocket_auth_fix_verification.py::test_jwt_secret_consistency_verification FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_1011_error_risk_prediction FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_chat_functionality_readiness FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_monitoring_observability_readiness FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_production_scalability_readiness FAILED
test_gcp_redis_websocket_golden_path_simple.py::test_gcp_redis_websocket_readiness_assessment FAILED

==================================================
0 passed, 6 failed in 2.04s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Authentication | 1 | 0 | 1 | 0.0% |
| WebSocket | 5 | 0 | 5 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*