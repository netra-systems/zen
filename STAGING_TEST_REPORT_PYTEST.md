# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-15 17:28:01
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 6
- **Passed:** 1 (16.7%)
- **Failed:** 5 (83.3%)
- **Skipped:** 0
- **Duration:** 89.11 seconds
- **Pass Rate:** 16.7%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_services_responding_fast | FAIL failed | 13.710s | test_infrastructure_improvements_e2e.py |
| test_staging_deployment_health_comprehensive | FAIL failed | 4.482s | test_infrastructure_improvements_e2e.py |
| test_staging_websocket_connectivity_improved | FAIL failed | 0.011s | test_infrastructure_improvements_e2e.py |
| test_staging_container_resource_efficiency | PASS passed | 5.266s | test_infrastructure_improvements_e2e.py |
| test_staging_deployment_stability_post_cleanup | FAIL failed | 41.507s | test_infrastructure_improvements_e2e.py |
| test_staging_auth_service_performance | FAIL failed | 10.317s | test_infrastructure_improvements_e2e.py |

## Failed Tests Details

### FAILED: test_staging_services_responding_fast
- **File:** C:\netra-apex\tests\e2e\staging\test_infrastructure_improvements_e2e.py
- **Duration:** 13.710s
- **Error:** tests\e2e\staging\test_infrastructure_improvements_e2e.py:63: in test_staging_services_responding_fast
    assert len(failed_services) == 0, f"Services failed health checks: {failed_services}"
E   AssertionError: Services failed health checks: ['backend', 'auth']
E   assert 2 == 0
E    +  where 2 = len(['backend', 'auth'])...

### FAILED: test_staging_deployment_health_comprehensive
- **File:** C:\netra-apex\tests\e2e\staging\test_infrastructure_improvements_e2e.py
- **Duration:** 4.482s
- **Error:** tests\e2e\staging\test_infrastructure_improvements_e2e.py:83: in test_staging_deployment_health_comprehensive
    assert response.status_code == 200, f"Backend health check failed: {response.status_code}"
E   AssertionError: Backend health check failed: 503
E   assert 503 == 200
E    +  where 503 = <Response [503]>.status_code...

### FAILED: test_staging_websocket_connectivity_improved
- **File:** C:\netra-apex\tests\e2e\staging\test_infrastructure_improvements_e2e.py
- **Duration:** 0.011s
- **Error:** tests\e2e\staging\test_infrastructure_improvements_e2e.py:121: in test_websocket_connection
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:541: in __await_impl__
    self.connection = await self.create_connection()
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^...

### FAILED: test_staging_deployment_stability_post_cleanup
- **File:** C:\netra-apex\tests\e2e\staging\test_infrastructure_improvements_e2e.py
- **Duration:** 41.507s
- **Error:** tests\e2e\staging\test_infrastructure_improvements_e2e.py:223: in test_staging_deployment_stability_post_cleanup
    assert success_rate >= 0.9, (
E   AssertionError: Success rate too low: 0.00% (should be ≥90%)
E   assert 0.0 >= 0.9...

### FAILED: test_staging_auth_service_performance
- **File:** C:\netra-apex\tests\e2e\staging\test_infrastructure_improvements_e2e.py
- **Duration:** 10.317s
- **Error:** C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\urllib3\connectionpool.py:534: in _make_request
    response = conn.getresponse()
               ^^^^^^^^^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\urllib3\connection.py:565: in getresponse
    httplib_response = super().getresponse()
                       ^^^^^^^^^^^^^^^^^^^^^
C:\Users\antho\miniconda3\Lib\http\client.py:1428: in getresponse
    response.begin()
C:\Users\antho\miniconda3\Lib\http\client...

## Pytest Output Format

### Run 1 (16:50:20)
```
test_priority1_critical.py::test_006_agent_configuration_real PASSED

==================================================
1 passed, 0 failed in 43.27s
```

### Run 2 (16:53:31)
```
test_infrastructure_improvements_e2e.py::test_staging_services_responding_fast FAILED
test_infrastructure_improvements_e2e.py::test_staging_deployment_health_comprehensive FAILED
test_infrastructure_improvements_e2e.py::test_staging_websocket_connectivity_improved FAILED
test_infrastructure_improvements_e2e.py::test_staging_container_resource_efficiency PASSED
test_infrastructure_improvements_e2e.py::test_staging_deployment_stability_post_cleanup FAILED
test_infrastructure_improvements_e2e.py::test_staging_auth_service_performance FAILED

==================================================
1 passed, 5 failed in 89.11s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 0 | 1 | 0.0% |
| Authentication | 1 | 0 | 1 | 0.0% |
| Performance | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
