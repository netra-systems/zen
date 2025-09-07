# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-06 23:14:52
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 121
- **Passed:** 116 (95.9%)
- **Failed:** 5 (4.1%)
- **Skipped:** 0
- **Duration:** 83.69 seconds
- **Pass Rate:** 95.9%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_websocket_connection_real | PASS passed | 0.478s | test_priority1_critical.py |
| test_002_websocket_authentication_real | FAIL failed | 0.001s | test_priority1_critical.py |
| test_003_websocket_message_send_real | FAIL failed | 0.002s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | FAIL failed | 0.001s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.306s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.535s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 0.652s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.487s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 1.233s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.633s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.790s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 0.730s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 0.974s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.600s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 0.933s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 1.248s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 4.194s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 4.227s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 0.727s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 5.626s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.040s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 0.842s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 0.850s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.259s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 0.637s | test_priority1_critical.py |
| test_001_websocket_connection_real | PASS passed | 0.282s | test_priority1_critical_REAL.py |
| test_002_websocket_authentication_real | PASS passed | 0.311s | test_priority1_critical_REAL.py |
| test_003_api_message_send_real | PASS passed | 0.275s | test_priority1_critical_REAL.py |
| test_004_api_health_comprehensive_real | PASS passed | 0.624s | test_priority1_critical_REAL.py |
| test_005_agent_discovery_real | PASS passed | 0.278s | test_priority1_critical_REAL.py |
| test_006_agent_configuration_real | PASS passed | 0.286s | test_priority1_critical_REAL.py |
| test_007_thread_management_real | PASS passed | 0.330s | test_priority1_critical_REAL.py |
| test_008_api_latency_real | PASS passed | 1.199s | test_priority1_critical_REAL.py |
| test_009_concurrent_requests_real | PASS passed | 0.308s | test_priority1_critical_REAL.py |
| test_010_error_handling_real | PASS passed | 0.532s | test_priority1_critical_REAL.py |
| test_011_service_discovery_real | PASS passed | 0.568s | test_priority1_critical_REAL.py |

### HIGH Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_026_jwt_authentication_real | PASS passed | 0.831s | test_priority2_high.py |
| test_027_oauth_google_login_real | PASS passed | 0.727s | test_priority2_high.py |
| test_028_token_refresh_real | PASS passed | 1.006s | test_priority2_high.py |
| test_029_token_expiry_real | PASS passed | 1.533s | test_priority2_high.py |
| test_030_logout_flow_real | PASS passed | 0.975s | test_priority2_high.py |
| test_031_session_security_real | PASS passed | 0.543s | test_priority2_high.py |
| test_032_https_certificate_validation_real | PASS passed | 0.495s | test_priority2_high.py |
| test_033_cors_policy_real | PASS passed | 1.819s | test_priority2_high.py |
| test_034_rate_limiting_real | PASS passed | 8.583s | test_priority2_high.py |
| test_035_websocket_security_real | FAIL failed | 0.305s | test_priority2_high.py |
| test_026_jwt_authentication | PASS passed | 0.155s | test_priority2_high_FAKE_BACKUP.py |
| test_027_oauth_google_login | PASS passed | 0.122s | test_priority2_high_FAKE_BACKUP.py |
| test_028_token_refresh | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_029_token_expiry | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_030_logout_flow | PASS passed | 0.158s | test_priority2_high_FAKE_BACKUP.py |
| test_031_session_security | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_032_cors_configuration | PASS passed | 0.207s | test_priority2_high_FAKE_BACKUP.py |
| test_033_api_authentication | PASS passed | 0.131s | test_priority2_high_FAKE_BACKUP.py |
| test_034_permission_checks | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_035_data_encryption | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_036_secure_websocket | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_037_input_sanitization | FAIL failed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_038_sql_injection_prevention | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |
| test_039_rate_limit_security | PASS passed | 0.134s | test_priority2_high_FAKE_BACKUP.py |
| test_040_audit_logging | PASS passed | 0.000s | test_priority2_high_FAKE_BACKUP.py |

### MEDIUM Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_056_response_time_p50 | PASS passed | 0.466s | test_priority4_medium.py |
| test_057_response_time_p95 | PASS passed | 0.465s | test_priority4_medium.py |
| test_058_response_time_p99 | PASS passed | 0.503s | test_priority4_medium.py |
| test_059_throughput_real | PASS passed | 5.253s | test_priority4_medium.py |
| test_060_concurrent_connections_real | PASS passed | 0.463s | test_priority4_medium.py |
| test_061_memory_usage_real | PASS passed | 0.555s | test_priority4_medium.py |
| test_062_cpu_usage | PASS passed | 0.000s | test_priority4_medium.py |
| test_063_database_connection_pool_real | PASS passed | 0.601s | test_priority4_medium.py |
| test_064_cache_hit_rate | PASS passed | 0.000s | test_priority4_medium.py |
| test_065_cold_start | PASS passed | 0.138s | test_priority4_medium.py |
| test_066_warm_start | PASS passed | 0.226s | test_priority4_medium.py |
| test_067_graceful_shutdown | PASS passed | 0.000s | test_priority4_medium.py |
| test_068_circuit_breaker_real | PASS passed | 2.859s | test_priority4_medium.py |
| test_069_retry_backoff | PASS passed | 0.000s | test_priority4_medium.py |
| test_070_connection_pooling_real | PASS passed | 3.405s | test_priority4_medium.py |

### LOW Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_086_health_endpoint | PASS passed | 0.137s | test_priority6_low.py |
| test_087_metrics_endpoint_real | PASS passed | 0.515s | test_priority6_low.py |
| test_088_logging_pipeline_real | PASS passed | 1.081s | test_priority6_low.py |
| test_089_distributed_tracing | PASS passed | 0.001s | test_priority6_low.py |
| test_090_error_tracking | PASS passed | 0.001s | test_priority6_low.py |
| test_091_performance_monitoring | PASS passed | 0.001s | test_priority6_low.py |
| test_092_alerting | PASS passed | 0.000s | test_priority6_low.py |
| test_093_dashboard_data | PASS passed | 0.000s | test_priority6_low.py |
| test_094_api_documentation | PASS passed | 0.251s | test_priority6_low.py |
| test_095_version_endpoint | PASS passed | 0.329s | test_priority6_low.py |
| test_096_feature_flags_real | PASS passed | 0.794s | test_priority6_low.py |
| test_097_a_b_testing | PASS passed | 0.000s | test_priority6_low.py |
| test_098_analytics_events | PASS passed | 0.000s | test_priority6_low.py |
| test_099_compliance_reporting | PASS passed | 0.000s | test_priority6_low.py |
| test_100_system_diagnostics | PASS passed | 0.127s | test_priority6_low.py |

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_041_multi_agent_workflow_real | PASS passed | 0.767s | test_priority3_medium_high.py |
| test_042_agent_handoff_real | PASS passed | 0.629s | test_priority3_medium_high.py |
| test_043_parallel_agent_execution_real | PASS passed | 0.671s | test_priority3_medium_high.py |
| test_044_sequential_agent_chain_real | PASS passed | 0.788s | test_priority3_medium_high.py |
| test_045_agent_dependencies_real | PASS passed | 0.624s | test_priority3_medium_high.py |
| test_046_agent_communication | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_047_workflow_branching | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_048_workflow_loops | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_049_agent_timeout | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_050_agent_retry | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_051_agent_fallback | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_052_resource_allocation | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_053_priority_scheduling | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_054_load_balancing | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_055_agent_monitoring | PASS passed | 0.239s | test_priority3_medium_high.py |
| test_071_message_storage_real | PASS passed | 0.841s | test_priority5_medium_low.py |
| test_072_thread_storage_real | PASS passed | 0.930s | test_priority5_medium_low.py |
| test_073_user_profile_storage_real | PASS passed | 1.264s | test_priority5_medium_low.py |
| test_074_file_upload | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_075_file_retrieval | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_076_data_export | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_077_data_import | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_078_backup_creation | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_079_backup_restoration | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_080_data_retention | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_081_data_deletion | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_082_search_functionality | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_083_filtering | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_084_pagination | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_085_sorting | PASS passed | 0.000s | test_priority5_medium_low.py |

## Failed Tests Details

### FAILED: test_002_websocket_authentication_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.001s
- **Error:** tests\e2e\staging\test_priority1_critical.py:132: in test_002_websocket_authentication_real
    assert duration > 0.1, f"Test too fast ({duration:.3f}s) - likely fake!"
E   AssertionError: Test too fast (0.000s) - likely fake!
E   assert 0.0 > 0.1...

### FAILED: test_003_websocket_message_send_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.002s
- **Error:** tests\e2e\staging\test_priority1_critical.py:184: in test_003_websocket_message_send_real
    assert duration > 0.1, f"Test too fast ({duration:.3f}s) - likely fake!"
E   AssertionError: Test too fast (0.000s) - likely fake!
E   assert 0.0 > 0.1...

### FAILED: test_004_websocket_concurrent_connections_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority1_critical.py
- **Duration:** 0.001s
- **Error:** tests\e2e\staging\test_priority1_critical.py:236: in test_004_websocket_concurrent_connections_real
    assert duration > 0.2, f"Test too fast ({duration:.3f}s) for 5 concurrent connections!"
E   AssertionError: Test too fast (0.000s) for 5 concurrent connections!
E   assert 0.0 > 0.2...

### FAILED: test_035_websocket_security_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority2_high.py
- **Duration:** 0.305s
- **Error:** tests\e2e\staging\test_priority2_high.py:844: in test_035_websocket_security_real
    assert len(websocket_results) > 2, "Should perform multiple WebSocket security tests"
E   AssertionError: Should perform multiple WebSocket security tests
E   assert 2 > 2
E    +  where 2 = len({'general_error': 'server rejected WebSocket connection: HTTP 403', 'secure_protocol': True})...

### FAILED: test_037_input_sanitization
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority2_high_FAKE_BACKUP.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_priority2_high_FAKE_BACKUP.py:248: in test_037_input_sanitization
    assert "javascript:" not in sanitized or sanitized != malicious_input
E   assert ('javascript:' not in "javascript:alert('xss')"
E     
E     'javascript:' is contained here:
E       javascript:alert('xss') or "javascript:alert('xss')" != "javascript:alert('xss')")...

## Pytest Output Format

```
test_priority1_critical.py::test_001_websocket_connection_real PASSED
test_priority1_critical.py::test_002_websocket_authentication_real FAILED
test_priority1_critical.py::test_003_websocket_message_send_real FAILED
test_priority1_critical.py::test_004_websocket_concurrent_connections_real FAILED
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
test_priority1_critical_REAL.py::test_001_websocket_connection_real PASSED
test_priority1_critical_REAL.py::test_002_websocket_authentication_real PASSED
test_priority1_critical_REAL.py::test_003_api_message_send_real PASSED
test_priority1_critical_REAL.py::test_004_api_health_comprehensive_real PASSED
test_priority1_critical_REAL.py::test_005_agent_discovery_real PASSED
test_priority1_critical_REAL.py::test_006_agent_configuration_real PASSED
test_priority1_critical_REAL.py::test_007_thread_management_real PASSED
test_priority1_critical_REAL.py::test_008_api_latency_real PASSED
test_priority1_critical_REAL.py::test_009_concurrent_requests_real PASSED
test_priority1_critical_REAL.py::test_010_error_handling_real PASSED
test_priority1_critical_REAL.py::test_011_service_discovery_real PASSED
test_priority2_high.py::test_026_jwt_authentication_real PASSED
test_priority2_high.py::test_027_oauth_google_login_real PASSED
test_priority2_high.py::test_028_token_refresh_real PASSED
test_priority2_high.py::test_029_token_expiry_real PASSED
test_priority2_high.py::test_030_logout_flow_real PASSED
test_priority2_high.py::test_031_session_security_real PASSED
test_priority2_high.py::test_032_https_certificate_validation_real PASSED
test_priority2_high.py::test_033_cors_policy_real PASSED
test_priority2_high.py::test_034_rate_limiting_real PASSED
test_priority2_high.py::test_035_websocket_security_real FAILED
test_priority2_high_FAKE_BACKUP.py::test_026_jwt_authentication PASSED
test_priority2_high_FAKE_BACKUP.py::test_027_oauth_google_login PASSED
test_priority2_high_FAKE_BACKUP.py::test_028_token_refresh PASSED
test_priority2_high_FAKE_BACKUP.py::test_029_token_expiry PASSED
test_priority2_high_FAKE_BACKUP.py::test_030_logout_flow PASSED
test_priority2_high_FAKE_BACKUP.py::test_031_session_security PASSED
test_priority2_high_FAKE_BACKUP.py::test_032_cors_configuration PASSED
test_priority2_high_FAKE_BACKUP.py::test_033_api_authentication PASSED
test_priority2_high_FAKE_BACKUP.py::test_034_permission_checks PASSED
test_priority2_high_FAKE_BACKUP.py::test_035_data_encryption PASSED
test_priority2_high_FAKE_BACKUP.py::test_036_secure_websocket PASSED
test_priority2_high_FAKE_BACKUP.py::test_037_input_sanitization FAILED
test_priority2_high_FAKE_BACKUP.py::test_038_sql_injection_prevention PASSED
test_priority2_high_FAKE_BACKUP.py::test_039_rate_limit_security PASSED
test_priority2_high_FAKE_BACKUP.py::test_040_audit_logging PASSED
test_priority3_medium_high.py::test_041_multi_agent_workflow_real PASSED
test_priority3_medium_high.py::test_042_agent_handoff_real PASSED
test_priority3_medium_high.py::test_043_parallel_agent_execution_real PASSED
test_priority3_medium_high.py::test_044_sequential_agent_chain_real PASSED
test_priority3_medium_high.py::test_045_agent_dependencies_real PASSED
test_priority3_medium_high.py::test_046_agent_communication PASSED
test_priority3_medium_high.py::test_047_workflow_branching PASSED
test_priority3_medium_high.py::test_048_workflow_loops PASSED
test_priority3_medium_high.py::test_049_agent_timeout PASSED
test_priority3_medium_high.py::test_050_agent_retry PASSED
test_priority3_medium_high.py::test_051_agent_fallback PASSED
test_priority3_medium_high.py::test_052_resource_allocation PASSED
test_priority3_medium_high.py::test_053_priority_scheduling PASSED
test_priority3_medium_high.py::test_054_load_balancing PASSED
test_priority3_medium_high.py::test_055_agent_monitoring PASSED
test_priority4_medium.py::test_056_response_time_p50 PASSED
test_priority4_medium.py::test_057_response_time_p95 PASSED
test_priority4_medium.py::test_058_response_time_p99 PASSED
test_priority4_medium.py::test_059_throughput_real PASSED
test_priority4_medium.py::test_060_concurrent_connections_real PASSED
test_priority4_medium.py::test_061_memory_usage_real PASSED
test_priority4_medium.py::test_062_cpu_usage PASSED
test_priority4_medium.py::test_063_database_connection_pool_real PASSED
test_priority4_medium.py::test_064_cache_hit_rate PASSED
test_priority4_medium.py::test_065_cold_start PASSED
test_priority4_medium.py::test_066_warm_start PASSED
test_priority4_medium.py::test_067_graceful_shutdown PASSED
test_priority4_medium.py::test_068_circuit_breaker_real PASSED
test_priority4_medium.py::test_069_retry_backoff PASSED
test_priority4_medium.py::test_070_connection_pooling_real PASSED
test_priority5_medium_low.py::test_071_message_storage_real PASSED
test_priority5_medium_low.py::test_072_thread_storage_real PASSED
test_priority5_medium_low.py::test_073_user_profile_storage_real PASSED
test_priority5_medium_low.py::test_074_file_upload PASSED
test_priority5_medium_low.py::test_075_file_retrieval PASSED
test_priority5_medium_low.py::test_076_data_export PASSED
test_priority5_medium_low.py::test_077_data_import PASSED
test_priority5_medium_low.py::test_078_backup_creation PASSED
test_priority5_medium_low.py::test_079_backup_restoration PASSED
test_priority5_medium_low.py::test_080_data_retention PASSED
test_priority5_medium_low.py::test_081_data_deletion PASSED
test_priority5_medium_low.py::test_082_search_functionality PASSED
test_priority5_medium_low.py::test_083_filtering PASSED
test_priority5_medium_low.py::test_084_pagination PASSED
test_priority5_medium_low.py::test_085_sorting PASSED
test_priority6_low.py::test_086_health_endpoint PASSED
test_priority6_low.py::test_087_metrics_endpoint_real PASSED
test_priority6_low.py::test_088_logging_pipeline_real PASSED
test_priority6_low.py::test_089_distributed_tracing PASSED
test_priority6_low.py::test_090_error_tracking PASSED
test_priority6_low.py::test_091_performance_monitoring PASSED
test_priority6_low.py::test_092_alerting PASSED
test_priority6_low.py::test_093_dashboard_data PASSED
test_priority6_low.py::test_094_api_documentation PASSED
test_priority6_low.py::test_095_version_endpoint PASSED
test_priority6_low.py::test_096_feature_flags_real PASSED
test_priority6_low.py::test_097_a_b_testing PASSED
test_priority6_low.py::test_098_analytics_events PASSED
test_priority6_low.py::test_099_compliance_reporting PASSED
test_priority6_low.py::test_100_system_diagnostics PASSED

==================================================
116 passed, 5 failed in 83.69s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 8 | 4 | 4 | 50.0% |
| Agent | 19 | 19 | 0 | 100.0% |
| Authentication | 7 | 6 | 1 | 85.7% |
| Performance | 6 | 6 | 0 | 100.0% |
| Security | 7 | 6 | 1 | 85.7% |
| Data | 5 | 5 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
