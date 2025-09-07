# Top 100 E2E Staging Tests - Execution Report

**Generated:** 2025-09-05 14:50:15
**Environment:** Staging - https://netra-backend-staging-pnovr5vsba-uc.a.run.app
**Test Framework:** Pytest unknown

## Executive Summary

- **Total Tests:** 158
- **Passed:** 154
- **Failed:** 4
- **Skipped:** 0
- **Duration:** 41.62 seconds
- **Pass Rate:** 97.5%

## Test Results

### Pytest Output

```
tests/e2e/staging/test_10_critical_path_staging.py::TestCriticalPathStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_10_critical_path_staging.py::TestCriticalPathStaging::test_critical_api_endpoints PASSED [0.00s]
tests/e2e/staging/test_10_critical_path_staging.py::TestCriticalPathStaging::test_end_to_end_message_flow PASSED [0.00s]
tests/e2e/staging/test_10_critical_path_staging.py::TestCriticalPathStaging::test_critical_performance_targets PASSED [0.00s]
tests/e2e/staging/test_10_critical_path_staging.py::TestCriticalPathStaging::test_critical_error_handling PASSED [0.00s]
tests/e2e/staging/test_10_critical_path_staging.py::TestCriticalPathStaging::test_business_critical_features PASSED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_health_check PASSED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_websocket_connection PASSED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_api_endpoints_for_agents PASSED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_websocket_event_simulation PASSED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_concurrent_connections PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_message_endpoints PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_message_structure_validation PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_message_flow_simulation PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_thread_management PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_error_message_handling PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_agent_discovery PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_agent_configuration PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_pipeline_stages PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_agent_lifecycle PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_pipeline_error_handling PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_pipeline_metrics PASSED [0.00s]
tests/e2e/staging/test_4_agent_orchestration_staging.py::TestAgentOrchestrationStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_4_agent_orchestration_staging.py::TestAgentOrchestrationStaging::test_agent_discovery_and_listing PASSED [0.00s]
tests/e2e/staging/test_4_agent_orchestration_staging.py::TestAgentOrchestrationStaging::test_orchestration_workflow_states PASSED [0.00s]
tests/e2e/staging/test_4_agent_orchestration_staging.py::TestAgentOrchestrationStaging::test_agent_communication_patterns PASSED [0.00s]
tests/e2e/staging/test_4_agent_orchestration_staging.py::TestAgentOrchestrationStaging::test_orchestration_error_scenarios PASSED [0.00s]
tests/e2e/staging/test_4_agent_orchestration_staging.py::TestAgentOrchestrationStaging::test_multi_agent_coordination_metrics PASSED [0.00s]
tests/e2e/staging/test_5_response_streaming_staging.py::TestResponseStreamingStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_5_response_streaming_staging.py::TestResponseStreamingStaging::test_streaming_protocols PASSED [0.00s]
tests/e2e/staging/test_5_response_streaming_staging.py::TestResponseStreamingStaging::test_chunk_handling PASSED [0.00s]
tests/e2e/staging/test_5_response_streaming_staging.py::TestResponseStreamingStaging::test_streaming_performance_metrics PASSED [0.00s]
tests/e2e/staging/test_5_response_streaming_staging.py::TestResponseStreamingStaging::test_backpressure_handling PASSED [0.00s]
tests/e2e/staging/test_5_response_streaming_staging.py::TestResponseStreamingStaging::test_stream_recovery PASSED [0.00s]
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_failure_detection PASSED [0.00s]
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_retry_strategies FAILED [0.00s]
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_circuit_breaker PASSED [0.00s]
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_graceful_degradation PASSED [0.00s]
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_recovery_metrics PASSED [0.00s]
tests/e2e/staging/test_7_startup_resilience_staging.py::TestStartupResilienceStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_7_startup_resilience_staging.py::TestStartupResilienceStaging::test_startup_sequence PASSED [0.00s]
tests/e2e/staging/test_7_startup_resilience_staging.py::TestStartupResilienceStaging::test_dependency_validation PASSED [0.00s]
tests/e2e/staging/test_7_startup_resilience_staging.py::TestStartupResilienceStaging::test_cold_start_performance PASSED [0.00s]
tests/e2e/staging/test_7_startup_resilience_staging.py::TestStartupResilienceStaging::test_startup_failure_handling PASSED [0.00s]
tests/e2e/staging/test_7_startup_resilience_staging.py::TestStartupResilienceStaging::test_health_check_endpoints PASSED [0.00s]
tests/e2e/staging/test_8_lifecycle_events_staging.py::TestLifecycleEventsStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_8_lifecycle_events_staging.py::TestLifecycleEventsStaging::test_event_types PASSED [0.00s]
tests/e2e/staging/test_8_lifecycle_events_staging.py::TestLifecycleEventsStaging::test_event_sequencing PASSED [0.00s]
tests/e2e/staging/test_8_lifecycle_events_staging.py::TestLifecycleEventsStaging::test_event_metadata PASSED [0.00s]
tests/e2e/staging/test_8_lifecycle_events_staging.py::TestLifecycleEventsStaging::test_event_filtering PASSED [0.00s]
tests/e2e/staging/test_8_lifecycle_events_staging.py::TestLifecycleEventsStaging::test_event_persistence PASSED [0.00s]
tests/e2e/staging/test_9_coordination_staging.py::TestCoordinationStaging::test_basic_functionality PASSED [0.00s]
tests/e2e/staging/test_9_coordination_staging.py::TestCoordinationStaging::test_coordination_patterns PASSED [0.00s]
tests/e2e/staging/test_9_coordination_staging.py::TestCoordinationStaging::test_task_distribution PASSED [0.00s]
tests/e2e/staging/test_9_coordination_staging.py::TestCoordinationStaging::test_synchronization_primitives PASSED [0.00s]
tests/e2e/staging/test_9_coordination_staging.py::TestCoordinationStaging::test_consensus_mechanisms PASSED [0.00s]
tests/e2e/staging/test_9_coordination_staging.py::TestCoordinationStaging::test_coordination_metrics PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalWebSocket::test_001_websocket_connection PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalWebSocket::test_002_websocket_authentication PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalWebSocket::test_003_websocket_message_send PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalWebSocket::test_004_websocket_message_receive PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_005_agent_startup PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_006_agent_execution PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_007_agent_response PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_008_agent_streaming PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_009_agent_completion PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_010_tool_execution PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalAgent::test_011_tool_results PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalMessaging::test_012_message_persistence PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalMessaging::test_013_thread_creation PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalMessaging::test_014_thread_switching PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalMessaging::test_015_thread_history PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalMessaging::test_016_user_context_isolation PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalScalability::test_017_concurrent_users PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalScalability::test_018_rate_limiting PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalScalability::test_019_error_messages PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalScalability::test_020_reconnection PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalScalability::test_021_session_persistence PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_022_agent_cancellation PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_023_partial_results PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_024_message_ordering PASSED [0.00s]
tests/e2e/staging/test_priority1_critical.py::TestCriticalUserExperience::test_025_event_delivery PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighAuthentication::test_026_jwt_authentication PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighAuthentication::test_027_oauth_google_login PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighAuthentication::test_028_token_refresh PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighAuthentication::test_029_token_expiry PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighAuthentication::test_030_logout_flow PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurity::test_031_session_security PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurity::test_032_cors_configuration PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurity::test_033_api_authentication PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurity::test_034_permission_checks PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurity::test_035_data_encryption PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurityAdvanced::test_036_secure_websocket PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurityAdvanced::test_037_input_sanitization FAILED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurityAdvanced::test_038_sql_injection_prevention PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurityAdvanced::test_039_rate_limit_security PASSED [0.00s]
tests/e2e/staging/test_priority2_high.py::TestHighSecurityAdvanced::test_040_audit_logging PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighOrchestration::test_041_multi_agent_workflow PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighOrchestration::test_042_agent_handoff PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighOrchestration::test_043_parallel_agent_execution PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighOrchestration::test_044_sequential_agent_chain PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighOrchestration::test_045_agent_dependencies PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighCommunication::test_046_agent_communication PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighCommunication::test_047_workflow_branching PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighCommunication::test_048_workflow_loops PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighCommunication::test_049_agent_timeout PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighCommunication::test_050_agent_retry PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighResilience::test_051_agent_fallback PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighResilience::test_052_resource_allocation PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighResilience::test_053_priority_scheduling PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighResilience::test_054_load_balancing PASSED [0.00s]
tests/e2e/staging/test_priority3_medium_high.py::TestMediumHighResilience::test_055_agent_monitoring PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumPerformance::test_056_response_time_p50 PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumPerformance::test_057_response_time_p95 PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumPerformance::test_058_response_time_p99 PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumPerformance::test_059_throughput PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumPerformance::test_060_concurrent_connections PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumResources::test_061_memory_usage PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumResources::test_062_cpu_usage PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumResources::test_063_database_connection_pool PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumResources::test_064_cache_hit_rate PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumResources::test_065_cold_start PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumReliability::test_066_warm_start PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumReliability::test_067_graceful_shutdown PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumReliability::test_068_circuit_breaker PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumReliability::test_069_retry_backoff PASSED [0.00s]
tests/e2e/staging/test_priority4_medium.py::TestMediumReliability::test_070_connection_pooling PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowStorage::test_071_message_storage PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowStorage::test_072_thread_storage PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowStorage::test_073_user_profile_storage PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowStorage::test_074_file_upload PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowStorage::test_075_file_retrieval PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowDataOps::test_076_data_export PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowDataOps::test_077_data_import PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowDataOps::test_078_backup_creation PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowDataOps::test_079_backup_restoration PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowDataOps::test_080_data_retention PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowCompliance::test_081_data_deletion PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowCompliance::test_082_search_functionality PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowCompliance::test_083_filtering PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowCompliance::test_084_pagination PASSED [0.00s]
tests/e2e/staging/test_priority5_medium_low.py::TestMediumLowCompliance::test_085_sorting PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowMonitoring::test_086_health_endpoint PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowMonitoring::test_087_metrics_endpoint PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowMonitoring::test_088_logging_pipeline PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowMonitoring::test_089_distributed_tracing PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowMonitoring::test_090_error_tracking PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowPerformanceMonitoring::test_091_performance_monitoring FAILED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowPerformanceMonitoring::test_092_alerting PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowPerformanceMonitoring::test_093_dashboard_data PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowPerformanceMonitoring::test_094_api_documentation PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowPerformanceMonitoring::test_095_version_endpoint PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowOperational::test_096_feature_flags FAILED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowOperational::test_097_a_b_testing PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowOperational::test_098_analytics_events PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowOperational::test_099_compliance_reporting PASSED [0.00s]
tests/e2e/staging/test_priority6_low.py::TestLowOperational::test_100_system_diagnostics PASSED [0.00s]

============================================================
154 passed, 4 failed in 41.62s
```

## Results by Priority

### [CRITICAL] Priority

**Results:** 25/25 passed

| Test | Result | Duration |
|------|--------|----------|
| test_001_websocket_connection | [PASS] passed | 0.000s |
| test_002_websocket_authentication | [PASS] passed | 0.000s |
| test_003_websocket_message_send | [PASS] passed | 0.000s |
| test_004_websocket_message_receive | [PASS] passed | 0.000s |
| test_005_agent_startup | [PASS] passed | 0.000s |
| test_006_agent_execution | [PASS] passed | 0.000s |
| test_007_agent_response | [PASS] passed | 0.000s |
| test_008_agent_streaming | [PASS] passed | 0.000s |
| test_009_agent_completion | [PASS] passed | 0.000s |
| test_010_tool_execution | [PASS] passed | 0.000s |
| test_011_tool_results | [PASS] passed | 0.000s |
| test_012_message_persistence | [PASS] passed | 0.000s |
| test_013_thread_creation | [PASS] passed | 0.000s |
| test_014_thread_switching | [PASS] passed | 0.000s |
| test_015_thread_history | [PASS] passed | 0.000s |
| test_016_user_context_isolation | [PASS] passed | 0.000s |
| test_017_concurrent_users | [PASS] passed | 0.000s |
| test_018_rate_limiting | [PASS] passed | 0.000s |
| test_019_error_messages | [PASS] passed | 0.000s |
| test_020_reconnection | [PASS] passed | 0.000s |
| test_021_session_persistence | [PASS] passed | 0.000s |
| test_022_agent_cancellation | [PASS] passed | 0.000s |
| test_023_partial_results | [PASS] passed | 0.000s |
| test_024_message_ordering | [PASS] passed | 0.000s |
| test_025_event_delivery | [PASS] passed | 0.000s |

### [HIGH] Priority

**Results:** 14/15 passed, 1 failed

| Test | Result | Duration |
|------|--------|----------|
| test_026_jwt_authentication | [PASS] passed | 0.000s |
| test_027_oauth_google_login | [PASS] passed | 0.000s |
| test_028_token_refresh | [PASS] passed | 0.000s |
| test_029_token_expiry | [PASS] passed | 0.000s |
| test_030_logout_flow | [PASS] passed | 0.000s |
| test_031_session_security | [PASS] passed | 0.000s |
| test_032_cors_configuration | [PASS] passed | 0.000s |
| test_033_api_authentication | [PASS] passed | 0.000s |
| test_034_permission_checks | [PASS] passed | 0.000s |
| test_035_data_encryption | [PASS] passed | 0.000s |
| test_036_secure_websocket | [PASS] passed | 0.000s |
| test_037_input_sanitization | [FAIL] failed | 0.000s |
| test_038_sql_injection_prevention | [PASS] passed | 0.000s |
| test_039_rate_limit_security | [PASS] passed | 0.000s |
| test_040_audit_logging | [PASS] passed | 0.000s |

### [MEDIUM] Priority

**Results:** 30/30 passed

| Test | Result | Duration |
|------|--------|----------|
| test_041_multi_agent_workflow | [PASS] passed | 0.000s |
| test_042_agent_handoff | [PASS] passed | 0.000s |
| test_043_parallel_agent_execution | [PASS] passed | 0.000s |
| test_044_sequential_agent_chain | [PASS] passed | 0.000s |
| test_045_agent_dependencies | [PASS] passed | 0.000s |
| test_046_agent_communication | [PASS] passed | 0.000s |
| test_047_workflow_branching | [PASS] passed | 0.000s |
| test_048_workflow_loops | [PASS] passed | 0.000s |
| test_049_agent_timeout | [PASS] passed | 0.000s |
| test_050_agent_retry | [PASS] passed | 0.000s |
| test_051_agent_fallback | [PASS] passed | 0.000s |
| test_052_resource_allocation | [PASS] passed | 0.000s |
| test_053_priority_scheduling | [PASS] passed | 0.000s |
| test_054_load_balancing | [PASS] passed | 0.000s |
| test_055_agent_monitoring | [PASS] passed | 0.000s |
| test_056_response_time_p50 | [PASS] passed | 0.000s |
| test_057_response_time_p95 | [PASS] passed | 0.000s |
| test_058_response_time_p99 | [PASS] passed | 0.000s |
| test_059_throughput | [PASS] passed | 0.000s |
| test_060_concurrent_connections | [PASS] passed | 0.000s |
| test_061_memory_usage | [PASS] passed | 0.000s |
| test_062_cpu_usage | [PASS] passed | 0.000s |
| test_063_database_connection_pool | [PASS] passed | 0.000s |
| test_064_cache_hit_rate | [PASS] passed | 0.000s |
| test_065_cold_start | [PASS] passed | 0.000s |
| test_066_warm_start | [PASS] passed | 0.000s |
| test_067_graceful_shutdown | [PASS] passed | 0.000s |
| test_068_circuit_breaker | [PASS] passed | 0.000s |
| test_069_retry_backoff | [PASS] passed | 0.000s |
| test_070_connection_pooling | [PASS] passed | 0.000s |

### [LOW] Priority

**Results:** 28/30 passed, 2 failed

| Test | Result | Duration |
|------|--------|----------|
| test_071_message_storage | [PASS] passed | 0.000s |
| test_072_thread_storage | [PASS] passed | 0.000s |
| test_073_user_profile_storage | [PASS] passed | 0.000s |
| test_074_file_upload | [PASS] passed | 0.000s |
| test_075_file_retrieval | [PASS] passed | 0.000s |
| test_076_data_export | [PASS] passed | 0.000s |
| test_077_data_import | [PASS] passed | 0.000s |
| test_078_backup_creation | [PASS] passed | 0.000s |
| test_079_backup_restoration | [PASS] passed | 0.000s |
| test_080_data_retention | [PASS] passed | 0.000s |
| test_081_data_deletion | [PASS] passed | 0.000s |
| test_082_search_functionality | [PASS] passed | 0.000s |
| test_083_filtering | [PASS] passed | 0.000s |
| test_084_pagination | [PASS] passed | 0.000s |
| test_085_sorting | [PASS] passed | 0.000s |
| test_086_health_endpoint | [PASS] passed | 0.000s |
| test_087_metrics_endpoint | [PASS] passed | 0.000s |
| test_088_logging_pipeline | [PASS] passed | 0.000s |
| test_089_distributed_tracing | [PASS] passed | 0.000s |
| test_090_error_tracking | [PASS] passed | 0.000s |
| test_091_performance_monitoring | [FAIL] failed | 0.000s |
| test_092_alerting | [PASS] passed | 0.000s |
| test_093_dashboard_data | [PASS] passed | 0.000s |
| test_094_api_documentation | [PASS] passed | 0.000s |
| test_095_version_endpoint | [PASS] passed | 0.000s |
| test_096_feature_flags | [FAIL] failed | 0.000s |
| test_097_a_b_testing | [PASS] passed | 0.000s |
| test_098_analytics_events | [PASS] passed | 0.000s |
| test_099_compliance_reporting | [PASS] passed | 0.000s |
| test_100_system_diagnostics | [PASS] passed | 0.000s |

### [NORMAL] Priority

**Results:** 57/58 passed, 1 failed

| Test | Result | Duration |
|------|--------|----------|
| test_basic_functionality | [PASS] passed | 0.000s |
| test_critical_api_endpoints | [PASS] passed | 0.000s |
| test_end_to_end_message_flow | [PASS] passed | 0.000s |
| test_critical_performance_targets | [PASS] passed | 0.000s |
| test_critical_error_handling | [PASS] passed | 0.000s |
| test_business_critical_features | [PASS] passed | 0.000s |
| test_health_check | [PASS] passed | 0.000s |
| test_websocket_connection | [PASS] passed | 0.000s |
| test_api_endpoints_for_agents | [PASS] passed | 0.000s |
| test_websocket_event_simulation | [PASS] passed | 0.000s |
| test_concurrent_connections | [PASS] passed | 0.000s |
| test_message_endpoints | [PASS] passed | 0.000s |
| test_message_structure_validation | [PASS] passed | 0.000s |
| test_message_flow_simulation | [PASS] passed | 0.000s |
| test_thread_management | [PASS] passed | 0.000s |
| test_error_message_handling | [PASS] passed | 0.000s |
| test_agent_discovery | [PASS] passed | 0.000s |
| test_agent_configuration | [PASS] passed | 0.000s |
| test_pipeline_stages | [PASS] passed | 0.000s |
| test_agent_lifecycle | [PASS] passed | 0.000s |
| test_pipeline_error_handling | [PASS] passed | 0.000s |
| test_pipeline_metrics | [PASS] passed | 0.000s |
| test_basic_functionality | [PASS] passed | 0.000s |
| test_agent_discovery_and_listing | [PASS] passed | 0.000s |
| test_orchestration_workflow_states | [PASS] passed | 0.000s |
| test_agent_communication_patterns | [PASS] passed | 0.000s |
| test_orchestration_error_scenarios | [PASS] passed | 0.000s |
| test_multi_agent_coordination_metrics | [PASS] passed | 0.000s |
| test_basic_functionality | [PASS] passed | 0.000s |
| test_streaming_protocols | [PASS] passed | 0.000s |
| test_chunk_handling | [PASS] passed | 0.000s |
| test_streaming_performance_metrics | [PASS] passed | 0.000s |
| test_backpressure_handling | [PASS] passed | 0.000s |
| test_stream_recovery | [PASS] passed | 0.000s |
| test_basic_functionality | [PASS] passed | 0.000s |
| test_failure_detection | [PASS] passed | 0.000s |
| test_retry_strategies | [FAIL] failed | 0.000s |
| test_circuit_breaker | [PASS] passed | 0.000s |
| test_graceful_degradation | [PASS] passed | 0.000s |
| test_recovery_metrics | [PASS] passed | 0.000s |
| test_basic_functionality | [PASS] passed | 0.000s |
| test_startup_sequence | [PASS] passed | 0.000s |
| test_dependency_validation | [PASS] passed | 0.000s |
| test_cold_start_performance | [PASS] passed | 0.000s |
| test_startup_failure_handling | [PASS] passed | 0.000s |
| test_health_check_endpoints | [PASS] passed | 0.000s |
| test_basic_functionality | [PASS] passed | 0.000s |
| test_event_types | [PASS] passed | 0.000s |
| test_event_sequencing | [PASS] passed | 0.000s |
| test_event_metadata | [PASS] passed | 0.000s |
| test_event_filtering | [PASS] passed | 0.000s |
| test_event_persistence | [PASS] passed | 0.000s |
| test_basic_functionality | [PASS] passed | 0.000s |
| test_coordination_patterns | [PASS] passed | 0.000s |
| test_task_distribution | [PASS] passed | 0.000s |
| test_synchronization_primitives | [PASS] passed | 0.000s |
| test_consensus_mechanisms | [PASS] passed | 0.000s |
| test_coordination_metrics | [PASS] passed | 0.000s |

## Failed Test Details

### [FAILED] tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_retry_strategies

**Error:**
```
..\staging_test_base.py:160: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_6_failure_recovery_staging.py:56: in test_retry_strategies
    assert "delay" in config or "initial_delay" in config
E   AssertionError: assert ('delay' in {'base_delay': 2, 'jitter_range': 1} or 'initial_delay' in {'base_delay': 2, 'jitter_range': 1})```

### [FAILED] tests/e2e/staging/test_priority2_high.py::TestHighSecurityAdvanced::test_037_input_sanitization

**Error:**
```
test_priority2_high.py:247: in test_037_input_sanitization
    assert "javascript:" not in sanitized or sanitized != malicious_input
E   assert ('javascript:' not in "javascript:alert('xss')"
E     
E     'javascript:' is contained here:
E       javascript:alert('xss') or "javascript:alert('xss')" != "javascript:alert('xss')")```

### [FAILED] tests/e2e/staging/test_priority6_low.py::TestLowPerformanceMonitoring::test_091_performance_monitoring

**Error:**
```
test_priority6_low.py:162: in test_091_performance_monitoring
    assert abs(apdex - performance["apdex_score"]) < 0.01
E   assert 0.020000000000000018 < 0.01
E    +  where 0.020000000000000018 = abs((0.97 - 0.95))```

### [FAILED] tests/e2e/staging/test_priority6_low.py::TestLowOperational::test_096_feature_flags

**Error:**
```
test_priority6_low.py:304: in test_096_feature_flags
    assert 0 <= config["rollout_percentage"] <= 100
                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   KeyError: 'rollout_percentage'```

## Test Coverage Analysis

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 20 | 20 | 0 | 100.0% |
| Agent | 31 | 31 | 0 | 100.0% |
| Message | 16 | 16 | 0 | 100.0% |
| Auth | 7 | 7 | 0 | 100.0% |
| Error | 6 | 6 | 0 | 100.0% |
| Performance | 13 | 12 | 1 | 92.3% |

## Environment Information

- **Python Version:** unknown
- **Platform:** unknown

## Recommendations

[SUCCESS] **System is production ready** - Pass rate exceeds 95%

### Priority Actions:

2. **Address 1 high priority failures**

---
*Report generated by Top 100 E2E Test Framework*
