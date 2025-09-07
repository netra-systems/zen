# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 00:15:06
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 230
- **Passed:** 192 (83.5%)
- **Failed:** 10 (4.3%)
- **Skipped:** 28
- **Duration:** 253.84 seconds
- **Pass Rate:** 83.5%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_staging_endpoint_actual_dns_resolution | PASS passed | 0.012s | test_expose_fake_tests.py |
| test_002_tcp_socket_connection_to_staging | PASS passed | 0.035s | test_expose_fake_tests.py |
| test_003_ssl_certificate_validation | PASS passed | 0.680s | test_expose_fake_tests.py |
| test_004_http_response_timing_validation | PASS passed | 2.550s | test_expose_fake_tests.py |
| test_005_websocket_handshake_timing | FAIL failed | 0.001s | test_expose_fake_tests.py |
| test_006_websocket_protocol_upgrade | PASS passed | 0.796s | test_expose_fake_tests.py |
| test_007_api_response_headers_validation | FAIL failed | 0.837s | test_expose_fake_tests.py |
| test_008_api_response_content_variation | PASS passed | 3.285s | test_expose_fake_tests.py |
| test_009_api_error_handling_authenticity | PASS passed | 2.164s | test_expose_fake_tests.py |
| test_010_sequential_request_timing | PASS passed | 3.207s | test_expose_fake_tests.py |
| test_011_concurrent_request_timing | PASS passed | 2.873s | test_expose_fake_tests.py |
| test_012_timeout_behavior_validation | PASS passed | 0.703s | test_expose_fake_tests.py |
| test_013_session_state_persistence | PASS passed | 1.039s | test_expose_fake_tests.py |
| test_014_server_state_consistency | PASS passed | 2.321s | test_expose_fake_tests.py |
| test_015_network_io_measurement | PASS passed | 2.391s | test_expose_fake_tests.py |
| test_016_memory_usage_during_requests | FAIL failed | 2.295s | test_expose_fake_tests.py |
| test_017_async_concurrency_validation | FAIL failed | 3.459s | test_expose_fake_tests.py |
| test_019_auth_required_endpoint_protection | PASS passed | 3.284s | test_expose_fake_tests.py |
| test_020_websocket_auth_enforcement | PASS passed | 0.001s | test_expose_fake_tests.py |
| test_999_comprehensive_fake_test_detection | FAIL failed | 1.534s | test_expose_fake_tests.py |
| test_001_websocket_connection_real | PASS passed | 1.622s | test_priority1_critical.py |
| test_002_websocket_authentication_real | PASS passed | 0.879s | test_priority1_critical.py |
| test_003_websocket_message_send_real | PASS passed | 0.884s | test_priority1_critical.py |
| test_004_websocket_concurrent_connections_real | PASS passed | 3.696s | test_priority1_critical.py |
| test_005_agent_discovery_real | PASS passed | 0.746s | test_priority1_critical.py |
| test_006_agent_configuration_real | PASS passed | 0.945s | test_priority1_critical.py |
| test_007_agent_execution_endpoints_real | PASS passed | 1.216s | test_priority1_critical.py |
| test_008_agent_streaming_capabilities_real | PASS passed | 0.887s | test_priority1_critical.py |
| test_009_agent_status_monitoring_real | PASS passed | 0.921s | test_priority1_critical.py |
| test_010_tool_execution_endpoints_real | PASS passed | 0.962s | test_priority1_critical.py |
| test_011_agent_performance_real | PASS passed | 1.920s | test_priority1_critical.py |
| test_012_message_persistence_real | PASS passed | 1.228s | test_priority1_critical.py |
| test_013_thread_creation_real | PASS passed | 1.325s | test_priority1_critical.py |
| test_014_thread_switching_real | PASS passed | 0.946s | test_priority1_critical.py |
| test_015_thread_history_real | PASS passed | 1.306s | test_priority1_critical.py |
| test_016_user_context_isolation_real | PASS passed | 2.028s | test_priority1_critical.py |
| test_017_concurrent_users_real | PASS passed | 13.736s | test_priority1_critical.py |
| test_018_rate_limiting_real | PASS passed | 5.288s | test_priority1_critical.py |
| test_019_error_handling_real | PASS passed | 1.268s | test_priority1_critical.py |
| test_020_connection_resilience_real | PASS passed | 10.376s | test_priority1_critical.py |
| test_021_session_persistence_real | PASS passed | 2.841s | test_priority1_critical.py |
| test_022_agent_lifecycle_management_real | PASS passed | 1.353s | test_priority1_critical.py |
| test_023_streaming_partial_results_real | PASS passed | 1.220s | test_priority1_critical.py |
| test_024_message_ordering_real | PASS passed | 2.788s | test_priority1_critical.py |
| test_025_critical_event_delivery_real | PASS passed | 1.082s | test_priority1_critical.py |
| test_001_websocket_connection_real | PASS passed | 0.745s | test_priority1_critical_REAL.py |
| test_002_websocket_authentication_real | PASS passed | 0.878s | test_priority1_critical_REAL.py |
| test_003_api_message_send_real | PASS passed | 0.788s | test_priority1_critical_REAL.py |
| test_004_api_health_comprehensive_real | PASS passed | 1.093s | test_priority1_critical_REAL.py |
| test_005_agent_discovery_real | PASS passed | 0.801s | test_priority1_critical_REAL.py |
| test_006_agent_configuration_real | PASS passed | 0.799s | test_priority1_critical_REAL.py |
| test_007_thread_management_real | PASS passed | 0.799s | test_priority1_critical_REAL.py |
| test_008_api_latency_real | PASS passed | 1.786s | test_priority1_critical_REAL.py |
| test_009_concurrent_requests_real | PASS passed | 0.942s | test_priority1_critical_REAL.py |
| test_010_error_handling_real | PASS passed | 1.041s | test_priority1_critical_REAL.py |
| test_011_service_discovery_real | PASS passed | 1.090s | test_priority1_critical_REAL.py |
| test_001_unified_data_agent_real_execution | FAIL failed | 0.810s | test_real_agent_execution_staging.py |
| test_002_optimization_agent_real_execution | FAIL failed | 0.773s | test_real_agent_execution_staging.py |
| test_003_multi_agent_coordination_real | FAIL failed | 0.729s | test_real_agent_execution_staging.py |

### HIGH Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_026_jwt_authentication_real | PASS passed | 1.844s | test_priority2_high.py |
| test_027_oauth_google_login_real | PASS passed | 1.234s | test_priority2_high.py |
| test_028_token_refresh_real | PASS passed | 1.414s | test_priority2_high.py |
| test_029_token_expiry_real | PASS passed | 1.732s | test_priority2_high.py |
| test_030_logout_flow_real | PASS passed | 1.385s | test_priority2_high.py |
| test_031_session_security_real | PASS passed | 0.980s | test_priority2_high.py |
| test_032_https_certificate_validation_real | PASS passed | 0.963s | test_priority2_high.py |
| test_033_cors_policy_real | PASS passed | 1.883s | test_priority2_high.py |
| test_034_rate_limiting_real | PASS passed | 8.655s | test_priority2_high.py |
| test_035_websocket_security_real | PASS passed | 0.759s | test_priority2_high.py |
| test_026_jwt_authentication | PASS passed | 0.129s | test_priority2_high_FAKE_BACKUP.py |
| test_027_oauth_google_login | PASS passed | 0.143s | test_priority2_high_FAKE_BACKUP.py |
| test_028_token_refresh | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_029_token_expiry | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_030_logout_flow | PASS passed | 0.138s | test_priority2_high_FAKE_BACKUP.py |
| test_031_session_security | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_032_cors_configuration | PASS passed | 0.133s | test_priority2_high_FAKE_BACKUP.py |
| test_033_api_authentication | PASS passed | 0.153s | test_priority2_high_FAKE_BACKUP.py |
| test_034_permission_checks | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_035_data_encryption | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_036_secure_websocket | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_037_input_sanitization | FAIL failed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_038_sql_injection_prevention | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |
| test_039_rate_limit_security | PASS passed | 0.151s | test_priority2_high_FAKE_BACKUP.py |
| test_040_audit_logging | PASS passed | 0.001s | test_priority2_high_FAKE_BACKUP.py |

### MEDIUM Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_056_response_time_p50 | PASS passed | 0.486s | test_priority4_medium.py |
| test_057_response_time_p95 | PASS passed | 0.574s | test_priority4_medium.py |
| test_058_response_time_p99 | PASS passed | 0.504s | test_priority4_medium.py |
| test_059_throughput_real | PASS passed | 5.815s | test_priority4_medium.py |
| test_060_concurrent_connections_real | PASS passed | 0.687s | test_priority4_medium.py |
| test_061_memory_usage_real | PASS passed | 0.885s | test_priority4_medium.py |
| test_062_cpu_usage | PASS passed | 0.001s | test_priority4_medium.py |
| test_063_database_connection_pool_real | PASS passed | 1.165s | test_priority4_medium.py |
| test_064_cache_hit_rate | PASS passed | 0.001s | test_priority4_medium.py |
| test_065_cold_start | PASS passed | 0.128s | test_priority4_medium.py |
| test_066_warm_start | PASS passed | 0.213s | test_priority4_medium.py |
| test_067_graceful_shutdown | PASS passed | 0.000s | test_priority4_medium.py |
| test_068_circuit_breaker_real | PASS passed | 3.118s | test_priority4_medium.py |
| test_069_retry_backoff | PASS passed | 0.000s | test_priority4_medium.py |
| test_070_connection_pooling_real | PASS passed | 3.482s | test_priority4_medium.py |

### LOW Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_086_health_endpoint | PASS passed | 0.124s | test_priority6_low.py |
| test_087_metrics_endpoint_real | PASS passed | 0.855s | test_priority6_low.py |
| test_088_logging_pipeline_real | PASS passed | 1.132s | test_priority6_low.py |
| test_089_distributed_tracing | PASS passed | 0.001s | test_priority6_low.py |
| test_090_error_tracking | PASS passed | 0.001s | test_priority6_low.py |
| test_091_performance_monitoring | PASS passed | 0.001s | test_priority6_low.py |
| test_092_alerting | PASS passed | 0.001s | test_priority6_low.py |
| test_093_dashboard_data | PASS passed | 0.001s | test_priority6_low.py |
| test_094_api_documentation | PASS passed | 0.226s | test_priority6_low.py |
| test_095_version_endpoint | PASS passed | 0.288s | test_priority6_low.py |
| test_096_feature_flags_real | PASS passed | 1.194s | test_priority6_low.py |
| test_097_a_b_testing | PASS passed | 0.001s | test_priority6_low.py |
| test_098_analytics_events | PASS passed | 0.000s | test_priority6_low.py |
| test_099_compliance_reporting | PASS passed | 0.001s | test_priority6_low.py |
| test_100_system_diagnostics | PASS passed | 0.172s | test_priority6_low.py |

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_basic_functionality | PASS passed | 0.636s | test_10_critical_path_staging.py |
| test_critical_api_endpoints | PASS passed | 1.037s | test_10_critical_path_staging.py |
| test_end_to_end_message_flow | PASS passed | 0.001s | test_10_critical_path_staging.py |
| test_critical_performance_targets | PASS passed | 0.001s | test_10_critical_path_staging.py |
| test_critical_error_handling | PASS passed | 0.002s | test_10_critical_path_staging.py |
| test_business_critical_features | PASS passed | 0.002s | test_10_critical_path_staging.py |
| test_health_check | PASS passed | 0.791s | test_1_websocket_events_staging.py |
| test_websocket_connection | PASS passed | 1.086s | test_1_websocket_events_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.880s | test_1_websocket_events_staging.py |
| test_websocket_event_flow_real | PASS passed | 0.640s | test_1_websocket_events_staging.py |
| test_concurrent_websocket_real | PASS passed | 3.923s | test_1_websocket_events_staging.py |
| test_message_endpoints | PASS passed | 0.716s | test_2_message_flow_staging.py |
| test_real_message_api_endpoints | PASS passed | 0.914s | test_2_message_flow_staging.py |
| test_real_websocket_message_flow | PASS passed | 0.821s | test_2_message_flow_staging.py |
| test_real_thread_management | PASS passed | 0.754s | test_2_message_flow_staging.py |
| test_real_error_handling_flow | PASS passed | 1.668s | test_2_message_flow_staging.py |
| test_real_agent_discovery | PASS passed | 1.009s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.872s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | PASS passed | 0.816s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | PASS passed | 1.762s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | PASS passed | 1.662s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 5.342s | test_3_agent_pipeline_staging.py |
| test_basic_functionality | PASS passed | 0.575s | test_4_agent_orchestration_staging.py |
| test_agent_discovery_and_listing | PASS passed | 0.682s | test_4_agent_orchestration_staging.py |
| test_orchestration_workflow_states | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_agent_communication_patterns | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_orchestration_error_scenarios | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_multi_agent_coordination_metrics | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_basic_functionality | PASS passed | 0.644s | test_5_response_streaming_staging.py |
| test_streaming_protocols | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_chunk_handling | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_streaming_performance_metrics | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_backpressure_handling | PASS passed | 0.003s | test_5_response_streaming_staging.py |
| test_stream_recovery | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_basic_functionality | PASS passed | 0.664s | test_6_failure_recovery_staging.py |
| test_failure_detection | PASS passed | 0.001s | test_6_failure_recovery_staging.py |
| test_retry_strategies | FAIL failed | 0.002s | test_6_failure_recovery_staging.py |
| test_circuit_breaker | PASS passed | 0.001s | test_6_failure_recovery_staging.py |
| test_graceful_degradation | PASS passed | 0.001s | test_6_failure_recovery_staging.py |
| test_recovery_metrics | PASS passed | 0.001s | test_6_failure_recovery_staging.py |
| test_basic_functionality | PASS passed | 0.680s | test_7_startup_resilience_staging.py |
| test_startup_sequence | PASS passed | 0.001s | test_7_startup_resilience_staging.py |
| test_dependency_validation | PASS passed | 0.001s | test_7_startup_resilience_staging.py |
| test_cold_start_performance | PASS passed | 0.001s | test_7_startup_resilience_staging.py |
| test_startup_failure_handling | PASS passed | 0.001s | test_7_startup_resilience_staging.py |
| test_health_check_endpoints | PASS passed | 0.597s | test_7_startup_resilience_staging.py |
| test_basic_functionality | PASS passed | 0.631s | test_8_lifecycle_events_staging.py |
| test_event_types | PASS passed | 0.001s | test_8_lifecycle_events_staging.py |
| test_event_sequencing | PASS passed | 0.001s | test_8_lifecycle_events_staging.py |
| test_event_metadata | PASS passed | 0.001s | test_8_lifecycle_events_staging.py |
| test_event_filtering | PASS passed | 0.001s | test_8_lifecycle_events_staging.py |
| test_event_persistence | PASS passed | 0.001s | test_8_lifecycle_events_staging.py |
| test_basic_functionality | PASS passed | 0.717s | test_9_coordination_staging.py |
| test_coordination_patterns | PASS passed | 0.001s | test_9_coordination_staging.py |
| test_task_distribution | PASS passed | 0.001s | test_9_coordination_staging.py |
| test_synchronization_primitives | PASS passed | 0.001s | test_9_coordination_staging.py |
| test_consensus_mechanisms | PASS passed | 0.001s | test_9_coordination_staging.py |
| test_coordination_metrics | PASS passed | 0.001s | test_9_coordination_staging.py |
| test_auth_google_login_route_returns_404 | SKIP skipped | 0.001s | test_auth_routes.py |
| test_multiple_oauth_routes_missing_404_pattern | SKIP skipped | 0.001s | test_auth_routes.py |
| test_auth_service_route_registration_incomplete | SKIP skipped | 0.000s | test_auth_routes.py |
| test_auth_service_route_mapping_configuration_error | SKIP skipped | 0.001s | test_auth_routes.py |
| test_auth_service_oauth_blueprint_not_registered | SKIP skipped | 0.000s | test_auth_routes.py |
| test_oauth_route_handler_import_or_dependency_missing | SKIP skipped | 0.001s | test_auth_routes.py |
| test_critical_environment_variables_missing | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_service_url_configuration_mismatch | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_database_configuration_inconsistent_across_services | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_environment_variable_type_validation_failures | SKIP skipped | 0.000s | test_environment_configuration.py |
| test_staging_specific_configuration_missing | SKIP skipped | 0.001s | test_environment_configuration.py |
| test_frontend_cannot_connect_to_backend_api_proxy_failure | SKIP skipped | 0.001s | test_frontend_backend_connection.py |
| test_frontend_proxy_configuration_mismatch | SKIP skipped | 0.000s | test_frontend_backend_connection.py |
| test_backend_service_not_listening_on_expected_ports | SKIP skipped | 0.001s | test_frontend_backend_connection.py |
| test_docker_container_network_isolation_issue | SKIP skipped | 0.000s | test_frontend_backend_connection.py |
| test_next_js_api_rewrites_configuration_broken | SKIP skipped | 0.000s | test_frontend_backend_connection.py |
| test_multiple_backend_connection_attempts_all_fail | SKIP skipped | 0.000s | test_frontend_backend_connection.py |
| test_backend_port_sequence_all_unavailable | SKIP skipped | 0.001s | test_network_connectivity_variations.py |
| test_intermittent_connection_failures_pattern | SKIP skipped | 0.001s | test_network_connectivity_variations.py |
| test_proxy_configuration_multiple_backends_fail | SKIP skipped | 0.001s | test_network_connectivity_variations.py |
| test_websocket_connection_also_fails | SKIP skipped | 0.001s | test_network_connectivity_variations.py |
| test_google_oauth_client_id_missing_from_environment | SKIP skipped | 0.001s | test_oauth_configuration.py |
| test_google_oauth_client_secret_missing_from_environment | SKIP skipped | 0.001s | test_oauth_configuration.py |
| test_oauth_configuration_incomplete_for_staging_deployment | SKIP skipped | 0.001s | test_oauth_configuration.py |
| test_oauth_google_authorization_url_construction_fails | SKIP skipped | 0.001s | test_oauth_configuration.py |
| test_oauth_token_exchange_endpoint_unreachable | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_redirect_uri_misconfiguration | SKIP skipped | 0.000s | test_oauth_configuration.py |
| test_oauth_scopes_configuration_incomplete | SKIP skipped | 0.001s | test_oauth_configuration.py |
| test_041_multi_agent_workflow_real | PASS passed | 0.986s | test_priority3_medium_high.py |
| test_042_agent_handoff_real | PASS passed | 0.992s | test_priority3_medium_high.py |
| test_043_parallel_agent_execution_real | PASS passed | 1.178s | test_priority3_medium_high.py |
| test_044_sequential_agent_chain_real | PASS passed | 5.340s | test_priority3_medium_high.py |
| test_045_agent_dependencies_real | PASS passed | 1.072s | test_priority3_medium_high.py |
| test_046_agent_communication | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_047_workflow_branching | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_048_workflow_loops | PASS passed | 0.000s | test_priority3_medium_high.py |
| test_049_agent_timeout | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_050_agent_retry | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_051_agent_fallback | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_052_resource_allocation | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_053_priority_scheduling | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_054_load_balancing | PASS passed | 0.001s | test_priority3_medium_high.py |
| test_055_agent_monitoring | PASS passed | 0.141s | test_priority3_medium_high.py |
| test_071_message_storage_real | PASS passed | 1.246s | test_priority5_medium_low.py |
| test_072_thread_storage_real | PASS passed | 1.381s | test_priority5_medium_low.py |
| test_073_user_profile_storage_real | PASS passed | 1.527s | test_priority5_medium_low.py |
| test_074_file_upload | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_075_file_retrieval | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_076_data_export | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_077_data_import | PASS passed | 0.000s | test_priority5_medium_low.py |
| test_078_backup_creation | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_079_backup_restoration | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_080_data_retention | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_081_data_deletion | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_082_search_functionality | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_083_filtering | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_084_pagination | PASS passed | 0.001s | test_priority5_medium_low.py |
| test_085_sorting | PASS passed | 0.001s | test_priority5_medium_low.py |

## Failed Tests Details

### FAILED: test_retry_strategies
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_6_failure_recovery_staging.py
- **Duration:** 0.002s
- **Error:** tests\e2e\staging_test_base.py:160: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_6_failure_recovery_staging.py:57: in test_retry_strategies
    assert "delay" in config or "initial_delay" in config
E   AssertionError: assert ('delay' in {'base_delay': 2, 'jitter_range': 1} or 'initial_delay' in {'base_delay': 2, 'jitter_range': 1})...

### FAILED: test_005_websocket_handshake_timing
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_expose_fake_tests.py
- **Duration:** 0.001s
- **Error:** tests\e2e\staging\test_expose_fake_tests.py:235: in test_005_websocket_handshake_timing
    async with websockets.connect(
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:541: in __await_impl__
    self.connection = await self.create_connection()
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\...

### FAILED: test_007_api_response_headers_validation
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_expose_fake_tests.py
- **Duration:** 0.837s
- **Error:** tests\e2e\staging\test_expose_fake_tests.py:363: in test_007_api_response_headers_validation
    assert time_diff < 300, f"Server date too old ({time_diff}s) - likely fake"
E   AssertionError: Server date too old (25201.651777s) - likely fake
E   assert 25201.651777 < 300...

### FAILED: test_016_memory_usage_during_requests
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_expose_fake_tests.py
- **Duration:** 2.295s
- **Error:** tests\e2e\staging\test_expose_fake_tests.py:725: in test_016_memory_usage_during_requests
    assert memory_increase > 1024 * 100, \
E   AssertionError: Memory increase too small (28672 bytes) after 3 clients - likely mocked
E   assert 28672 > (1024 * 100)...

### FAILED: test_017_async_concurrency_validation
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_expose_fake_tests.py
- **Duration:** 3.459s
- **Error:** tests\e2e\staging\test_expose_fake_tests.py:774: in test_017_async_concurrency_validation
    assert total_time < expected_sequential * 0.7, \
E   AssertionError: Not truly concurrent: 3.458164930343628s vs expected sequential 1.05s
E   assert 3.458164930343628 < (1.05 * 0.7)...

### FAILED: test_999_comprehensive_fake_test_detection
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_expose_fake_tests.py
- **Duration:** 1.534s
- **Error:** tests\e2e\staging\test_expose_fake_tests.py:976: in test_999_comprehensive_fake_test_detection
    assert real_evidence_count >= total_checks * 0.6, \
E   AssertionError: Insufficient evidence of real staging (4/10) - This appears to be running against FAKE TESTS!
E   assert 4 >= (10 * 0.6)...

### FAILED: test_037_input_sanitization
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_priority2_high_FAKE_BACKUP.py
- **Duration:** 0.001s
- **Error:** tests\e2e\staging\test_priority2_high_FAKE_BACKUP.py:248: in test_037_input_sanitization
    assert "javascript:" not in sanitized or sanitized != malicious_input
E   assert ('javascript:' not in "javascript:alert('xss')"
E     
E     'javascript:' is contained here:
E       javascript:alert('xss') or "javascript:alert('xss')" != "javascript:alert('xss')")...

### FAILED: test_001_unified_data_agent_real_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.810s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:348: in test_001_unified_data_agent_real_execution
    async with validator.create_authenticated_websocket() as ws:
..\..\..\..\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_real_agent_execution_staging.py:115: in create_authenticated_websocket
    websocket = await asyncio.wait_for(
..\..\..\..\miniconda3\Lib\asyncio\tasks.py:520: in wait_for
    retu...

### FAILED: test_002_optimization_agent_real_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.773s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:395: in test_002_optimization_agent_real_execution
    async with validator.create_authenticated_websocket() as ws:
..\..\..\..\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_real_agent_execution_staging.py:115: in create_authenticated_websocket
    websocket = await asyncio.wait_for(
..\..\..\..\miniconda3\Lib\asyncio\tasks.py:520: in wait_for
    retu...

### FAILED: test_003_multi_agent_coordination_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.729s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:436: in test_003_multi_agent_coordination_real
    async with validator.create_authenticated_websocket() as ws:
..\..\..\..\miniconda3\Lib\contextlib.py:210: in __aenter__
    return await anext(self.gen)
           ^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_real_agent_execution_staging.py:115: in create_authenticated_websocket
    websocket = await asyncio.wait_for(
..\..\..\..\miniconda3\Lib\asyncio\tasks.py:520: in wait_for
    return a...

## Pytest Output Format

```
test_10_critical_path_staging.py::test_basic_functionality PASSED
test_10_critical_path_staging.py::test_critical_api_endpoints PASSED
test_10_critical_path_staging.py::test_end_to_end_message_flow PASSED
test_10_critical_path_staging.py::test_critical_performance_targets PASSED
test_10_critical_path_staging.py::test_critical_error_handling PASSED
test_10_critical_path_staging.py::test_business_critical_features PASSED
test_1_websocket_events_staging.py::test_health_check PASSED
test_1_websocket_events_staging.py::test_websocket_connection PASSED
test_1_websocket_events_staging.py::test_api_endpoints_for_agents PASSED
test_1_websocket_events_staging.py::test_websocket_event_flow_real PASSED
test_1_websocket_events_staging.py::test_concurrent_websocket_real PASSED
test_2_message_flow_staging.py::test_message_endpoints PASSED
test_2_message_flow_staging.py::test_real_message_api_endpoints PASSED
test_2_message_flow_staging.py::test_real_websocket_message_flow PASSED
test_2_message_flow_staging.py::test_real_thread_management PASSED
test_2_message_flow_staging.py::test_real_error_handling_flow PASSED
test_3_agent_pipeline_staging.py::test_real_agent_discovery PASSED
test_3_agent_pipeline_staging.py::test_real_agent_configuration PASSED
test_3_agent_pipeline_staging.py::test_real_agent_pipeline_execution PASSED
test_3_agent_pipeline_staging.py::test_real_agent_lifecycle_monitoring PASSED
test_3_agent_pipeline_staging.py::test_real_pipeline_error_handling PASSED
test_3_agent_pipeline_staging.py::test_real_pipeline_metrics PASSED
test_4_agent_orchestration_staging.py::test_basic_functionality PASSED
test_4_agent_orchestration_staging.py::test_agent_discovery_and_listing PASSED
test_4_agent_orchestration_staging.py::test_orchestration_workflow_states PASSED
test_4_agent_orchestration_staging.py::test_agent_communication_patterns PASSED
test_4_agent_orchestration_staging.py::test_orchestration_error_scenarios PASSED
test_4_agent_orchestration_staging.py::test_multi_agent_coordination_metrics PASSED
test_5_response_streaming_staging.py::test_basic_functionality PASSED
test_5_response_streaming_staging.py::test_streaming_protocols PASSED
test_5_response_streaming_staging.py::test_chunk_handling PASSED
test_5_response_streaming_staging.py::test_streaming_performance_metrics PASSED
test_5_response_streaming_staging.py::test_backpressure_handling PASSED
test_5_response_streaming_staging.py::test_stream_recovery PASSED
test_6_failure_recovery_staging.py::test_basic_functionality PASSED
test_6_failure_recovery_staging.py::test_failure_detection PASSED
test_6_failure_recovery_staging.py::test_retry_strategies FAILED
test_6_failure_recovery_staging.py::test_circuit_breaker PASSED
test_6_failure_recovery_staging.py::test_graceful_degradation PASSED
test_6_failure_recovery_staging.py::test_recovery_metrics PASSED
test_7_startup_resilience_staging.py::test_basic_functionality PASSED
test_7_startup_resilience_staging.py::test_startup_sequence PASSED
test_7_startup_resilience_staging.py::test_dependency_validation PASSED
test_7_startup_resilience_staging.py::test_cold_start_performance PASSED
test_7_startup_resilience_staging.py::test_startup_failure_handling PASSED
test_7_startup_resilience_staging.py::test_health_check_endpoints PASSED
test_8_lifecycle_events_staging.py::test_basic_functionality PASSED
test_8_lifecycle_events_staging.py::test_event_types PASSED
test_8_lifecycle_events_staging.py::test_event_sequencing PASSED
test_8_lifecycle_events_staging.py::test_event_metadata PASSED
test_8_lifecycle_events_staging.py::test_event_filtering PASSED
test_8_lifecycle_events_staging.py::test_event_persistence PASSED
test_9_coordination_staging.py::test_basic_functionality PASSED
test_9_coordination_staging.py::test_coordination_patterns PASSED
test_9_coordination_staging.py::test_task_distribution PASSED
test_9_coordination_staging.py::test_synchronization_primitives PASSED
test_9_coordination_staging.py::test_consensus_mechanisms PASSED
test_9_coordination_staging.py::test_coordination_metrics PASSED
test_auth_routes.py::test_auth_google_login_route_returns_404 SKIPPED
test_auth_routes.py::test_multiple_oauth_routes_missing_404_pattern SKIPPED
test_auth_routes.py::test_auth_service_route_registration_incomplete SKIPPED
test_auth_routes.py::test_auth_service_route_mapping_configuration_error SKIPPED
test_auth_routes.py::test_auth_service_oauth_blueprint_not_registered SKIPPED
test_auth_routes.py::test_oauth_route_handler_import_or_dependency_missing SKIPPED
test_environment_configuration.py::test_critical_environment_variables_missing SKIPPED
test_environment_configuration.py::test_service_url_configuration_mismatch SKIPPED
test_environment_configuration.py::test_database_configuration_inconsistent_across_services SKIPPED
test_environment_configuration.py::test_environment_variable_type_validation_failures SKIPPED
test_environment_configuration.py::test_staging_specific_configuration_missing SKIPPED
test_expose_fake_tests.py::test_001_staging_endpoint_actual_dns_resolution PASSED
test_expose_fake_tests.py::test_002_tcp_socket_connection_to_staging PASSED
test_expose_fake_tests.py::test_003_ssl_certificate_validation PASSED
test_expose_fake_tests.py::test_004_http_response_timing_validation PASSED
test_expose_fake_tests.py::test_005_websocket_handshake_timing FAILED
test_expose_fake_tests.py::test_006_websocket_protocol_upgrade PASSED
test_expose_fake_tests.py::test_007_api_response_headers_validation FAILED
test_expose_fake_tests.py::test_008_api_response_content_variation PASSED
test_expose_fake_tests.py::test_009_api_error_handling_authenticity PASSED
test_expose_fake_tests.py::test_010_sequential_request_timing PASSED
test_expose_fake_tests.py::test_011_concurrent_request_timing PASSED
test_expose_fake_tests.py::test_012_timeout_behavior_validation PASSED
test_expose_fake_tests.py::test_013_session_state_persistence PASSED
test_expose_fake_tests.py::test_014_server_state_consistency PASSED
test_expose_fake_tests.py::test_015_network_io_measurement PASSED
test_expose_fake_tests.py::test_016_memory_usage_during_requests FAILED
test_expose_fake_tests.py::test_017_async_concurrency_validation FAILED
test_expose_fake_tests.py::test_019_auth_required_endpoint_protection PASSED
test_expose_fake_tests.py::test_020_websocket_auth_enforcement PASSED
test_expose_fake_tests.py::test_999_comprehensive_fake_test_detection FAILED
test_frontend_backend_connection.py::test_frontend_cannot_connect_to_backend_api_proxy_failure SKIPPED
test_frontend_backend_connection.py::test_frontend_proxy_configuration_mismatch SKIPPED
test_frontend_backend_connection.py::test_backend_service_not_listening_on_expected_ports SKIPPED
test_frontend_backend_connection.py::test_docker_container_network_isolation_issue SKIPPED
test_frontend_backend_connection.py::test_next_js_api_rewrites_configuration_broken SKIPPED
test_frontend_backend_connection.py::test_multiple_backend_connection_attempts_all_fail SKIPPED
test_network_connectivity_variations.py::test_backend_port_sequence_all_unavailable SKIPPED
test_network_connectivity_variations.py::test_intermittent_connection_failures_pattern SKIPPED
test_network_connectivity_variations.py::test_proxy_configuration_multiple_backends_fail SKIPPED
test_network_connectivity_variations.py::test_websocket_connection_also_fails SKIPPED
test_oauth_configuration.py::test_google_oauth_client_id_missing_from_environment SKIPPED
test_oauth_configuration.py::test_google_oauth_client_secret_missing_from_environment SKIPPED
test_oauth_configuration.py::test_oauth_configuration_incomplete_for_staging_deployment SKIPPED
test_oauth_configuration.py::test_oauth_google_authorization_url_construction_fails SKIPPED
test_oauth_configuration.py::test_oauth_token_exchange_endpoint_unreachable SKIPPED
test_oauth_configuration.py::test_oauth_redirect_uri_misconfiguration SKIPPED
test_oauth_configuration.py::test_oauth_scopes_configuration_incomplete SKIPPED
test_priority1_critical.py::test_001_websocket_connection_real PASSED
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
test_priority2_high.py::test_035_websocket_security_real PASSED
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
test_real_agent_execution_staging.py::test_001_unified_data_agent_real_execution FAILED
test_real_agent_execution_staging.py::test_002_optimization_agent_real_execution FAILED
test_real_agent_execution_staging.py::test_003_multi_agent_coordination_real FAILED

==================================================
192 passed, 10 failed, 28 skipped in 253.84s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 16 | 14 | 1 | 87.5% |
| Agent | 30 | 27 | 3 | 90.0% |
| Authentication | 23 | 10 | 0 | 43.5% |
| Performance | 9 | 9 | 0 | 100.0% |
| Security | 7 | 7 | 0 | 100.0% |
| Data | 6 | 5 | 0 | 83.3% |

---
*Report generated by pytest-staging framework v1.0*
