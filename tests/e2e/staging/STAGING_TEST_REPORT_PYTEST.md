# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 18:58:31
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 27
- **Passed:** 7 (25.9%)
- **Failed:** 9 (33.3%)
- **Skipped:** 11
- **Duration:** 82.36 seconds
- **Pass Rate:** 25.9%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_debug_jwt_secret_resolution | PASS passed | 0.000s | test_websocket_auth_fix.py |
| test_reproduce_websocket_403_error | PASS passed | 0.625s | test_websocket_auth_fix.py |
| test_create_jwt_with_backend_secret | PASS passed | 0.598s | test_websocket_auth_fix.py |

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_health_check | FAIL failed | 0.636s | test_1_websocket_events_staging.py |
| test_websocket_connection | FAIL failed | 0.655s | test_1_websocket_events_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.727s | test_1_websocket_events_staging.py |
| test_websocket_event_flow_real | FAIL failed | 0.769s | test_1_websocket_events_staging.py |
| test_concurrent_websocket_real | FAIL failed | 3.493s | test_1_websocket_events_staging.py |
| test_auth_google_login_route_returns_404 | SKIP skipped | 4.452s | test_auth_routes.py |
| test_multiple_oauth_routes_missing_404_pattern | SKIP skipped | 4.016s | test_auth_routes.py |
| test_auth_service_route_registration_incomplete | SKIP skipped | 4.012s | test_auth_routes.py |
| test_auth_service_route_mapping_configuration_error | SKIP skipped | 4.006s | test_auth_routes.py |
| test_auth_service_oauth_blueprint_not_registered | SKIP skipped | 4.003s | test_auth_routes.py |
| test_oauth_route_handler_import_or_dependency_missing | SKIP skipped | 4.013s | test_auth_routes.py |
| test_google_oauth_client_id_missing_from_environment | SKIP skipped | 4.015s | test_oauth_configuration.py |
| test_google_oauth_client_secret_missing_from_environment | SKIP skipped | 4.008s | test_oauth_configuration.py |
| test_oauth_configuration_incomplete_for_staging_deployment | SKIP skipped | 4.007s | test_oauth_configuration.py |
| test_oauth_google_authorization_url_construction_fails | SKIP skipped | 4.002s | test_oauth_configuration.py |
| test_oauth_token_exchange_endpoint_unreachable | FAIL failed | 0.000s | test_oauth_configuration.py |
| test_oauth_redirect_uri_misconfiguration | SKIP skipped | 4.008s | test_oauth_configuration.py |
| test_oauth_scopes_configuration_incomplete | FAIL failed | 0.000s | test_oauth_configuration.py |
| test_websocket_auth_consistency_fix | PASS passed | 0.822s | test_websocket_auth_consistency_fix.py |
| test_jwt_validation_methods_comparison | PASS passed | 13.372s | test_websocket_auth_consistency_fix.py |
| test_jwt_secret_consistency_verification | FAIL failed | 0.664s | test_websocket_auth_fix_verification.py |
| test_websocket_rest_jwt_parity | PASS passed | 1.046s | test_websocket_auth_fix_verification.py |
| test_websocket_auth_with_ssot_helper | FAIL failed | 1.655s | test_websocket_auth_ssot_fix.py |
| test_ssot_auth_flow_complete | FAIL failed | 0.143s | test_websocket_auth_ssot_fix.py |

## Failed Tests Details

### FAILED: test_health_check
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.636s
- **Error:** ..\staging_test_base.py:308: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:54: in test_health_check
    await self.verify_api_health()
..\staging_test_base.py:258: in verify_api_health
    assert response.status_code == 200
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AssertionError...

### FAILED: test_websocket_connection
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.655s
- **Error:** ..\staging_test_base.py:308: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:88: in test_websocket_connection
    await ws.send(json.dumps({"type": "ping"}))
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:476: in send
    async with self.send_context():
C:\Users\antho\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^...

### FAILED: test_websocket_event_flow_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.769s
- **Error:** ..\staging_test_base.py:308: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:238: in test_websocket_event_flow_real
    await ws.send(json.dumps(test_message))
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:476: in send
    async with self.send_context():
C:\Users\antho\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^...

### FAILED: test_concurrent_websocket_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 3.493s
- **Error:** ..\staging_test_base.py:308: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:376: in test_concurrent_websocket_real
    results = await asyncio.gather(*tasks)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:361: in test_connection
    await ws.send(json.dumps(ping_msg))
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:476: in send
    async with ...

### FAILED: test_oauth_token_exchange_endpoint_unreachable
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_oauth_configuration.py
- **Duration:** 0.000s
- **Error:** test_oauth_configuration.py:277: in test_oauth_token_exchange_endpoint_unreachable
    if not client_id:
           ^^^^^^^^^
E   NameError: name 'client_id' is not defined...

### FAILED: test_oauth_scopes_configuration_incomplete
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_oauth_configuration.py
- **Duration:** 0.000s
- **Error:** test_oauth_configuration.py:457: in test_oauth_scopes_configuration_incomplete
    if not configured_scopes_str:
           ^^^^^^^^^^^^^^^^^^^^^
E   NameError: name 'configured_scopes_str' is not defined...

### FAILED: test_jwt_secret_consistency_verification
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_auth_fix_verification.py
- **Duration:** 0.664s
- **Error:** ..\staging_test_base.py:308: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_websocket_auth_fix_verification.py:184: in test_jwt_secret_consistency_verification
    await ws.send(json.dumps(test_message))
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:476: in send
    async with self.send_context():
C:\Users\antho\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
         ...

### FAILED: test_websocket_auth_with_ssot_helper
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_auth_ssot_fix.py
- **Duration:** 1.655s
- **Error:** test_websocket_auth_ssot_fix.py:59: in test_websocket_auth_with_ssot_helper
    await ws.send(test_msg)
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:476: in send
    async with self.send_context():
C:\Users\antho\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:957: in send_context
    rai...

### FAILED: test_ssot_auth_flow_complete
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_websocket_auth_ssot_fix.py
- **Duration:** 0.143s
- **Error:** test_websocket_auth_ssot_fix.py:117: in test_ssot_auth_flow_complete
    assert success, "Complete WebSocket auth flow should succeed"
E   AssertionError: Complete WebSocket auth flow should succeed
E   assert False...

## Pytest Output Format

```
test_1_websocket_events_staging.py::test_health_check FAILED
test_1_websocket_events_staging.py::test_websocket_connection FAILED
test_1_websocket_events_staging.py::test_api_endpoints_for_agents PASSED
test_1_websocket_events_staging.py::test_websocket_event_flow_real FAILED
test_1_websocket_events_staging.py::test_concurrent_websocket_real FAILED
test_auth_routes.py::test_auth_google_login_route_returns_404 SKIPPED
test_auth_routes.py::test_multiple_oauth_routes_missing_404_pattern SKIPPED
test_auth_routes.py::test_auth_service_route_registration_incomplete SKIPPED
test_auth_routes.py::test_auth_service_route_mapping_configuration_error SKIPPED
test_auth_routes.py::test_auth_service_oauth_blueprint_not_registered SKIPPED
test_auth_routes.py::test_oauth_route_handler_import_or_dependency_missing SKIPPED
test_oauth_configuration.py::test_google_oauth_client_id_missing_from_environment SKIPPED
test_oauth_configuration.py::test_google_oauth_client_secret_missing_from_environment SKIPPED
test_oauth_configuration.py::test_oauth_configuration_incomplete_for_staging_deployment SKIPPED
test_oauth_configuration.py::test_oauth_google_authorization_url_construction_fails SKIPPED
test_oauth_configuration.py::test_oauth_token_exchange_endpoint_unreachable FAILED
test_oauth_configuration.py::test_oauth_redirect_uri_misconfiguration SKIPPED
test_oauth_configuration.py::test_oauth_scopes_configuration_incomplete FAILED
test_websocket_auth_consistency_fix.py::test_websocket_auth_consistency_fix PASSED
test_websocket_auth_consistency_fix.py::test_jwt_validation_methods_comparison PASSED
test_websocket_auth_fix.py::test_debug_jwt_secret_resolution PASSED
test_websocket_auth_fix.py::test_reproduce_websocket_403_error PASSED
test_websocket_auth_fix.py::test_create_jwt_with_backend_secret PASSED
test_websocket_auth_fix_verification.py::test_jwt_secret_consistency_verification FAILED
test_websocket_auth_fix_verification.py::test_websocket_rest_jwt_parity PASSED
test_websocket_auth_ssot_fix.py::test_websocket_auth_with_ssot_helper FAILED
test_websocket_auth_ssot_fix.py::test_ssot_auth_flow_complete FAILED

==================================================
7 passed, 9 failed, 11 skipped in 82.36s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 7 | 3 | 4 | 42.9% |
| Agent | 1 | 1 | 0 | 100.0% |
| Authentication | 21 | 5 | 5 | 23.8% |

---
*Report generated by pytest-staging framework v1.0*
