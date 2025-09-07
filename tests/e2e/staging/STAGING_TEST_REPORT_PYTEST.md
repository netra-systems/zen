# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 08:22:54
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 58
- **Passed:** 52 (89.7%)
- **Failed:** 6 (10.3%)
- **Skipped:** 0
- **Duration:** 44.62 seconds
- **Pass Rate:** 89.7%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_basic_functionality | PASS passed | 0.380s | test_10_critical_path_staging.py |
| test_critical_api_endpoints | PASS passed | 0.765s | test_10_critical_path_staging.py |
| test_end_to_end_message_flow | PASS passed | 0.000s | test_10_critical_path_staging.py |
| test_critical_performance_targets | PASS passed | 0.000s | test_10_critical_path_staging.py |
| test_critical_error_handling | PASS passed | 0.000s | test_10_critical_path_staging.py |
| test_business_critical_features | PASS passed | 0.000s | test_10_critical_path_staging.py |
| test_health_check | PASS passed | 0.542s | test_1_websocket_events_staging.py |
| test_websocket_connection | FAIL failed | 0.413s | test_1_websocket_events_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.556s | test_1_websocket_events_staging.py |
| test_websocket_event_flow_real | FAIL failed | 0.405s | test_1_websocket_events_staging.py |
| test_concurrent_websocket_real | FAIL failed | 1.842s | test_1_websocket_events_staging.py |
| test_message_endpoints | PASS passed | 0.422s | test_2_message_flow_staging.py |
| test_real_message_api_endpoints | PASS passed | 0.680s | test_2_message_flow_staging.py |
| test_real_websocket_message_flow | PASS passed | 0.360s | test_2_message_flow_staging.py |
| test_real_thread_management | PASS passed | 0.507s | test_2_message_flow_staging.py |
| test_real_error_handling_flow | PASS passed | 1.097s | test_2_message_flow_staging.py |
| test_real_agent_discovery | PASS passed | 0.655s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.593s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | FAIL failed | 0.331s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | FAIL failed | 1.072s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | FAIL failed | 1.008s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 3.332s | test_3_agent_pipeline_staging.py |
| test_basic_functionality | PASS passed | 0.315s | test_4_agent_orchestration_staging.py |
| test_agent_discovery_and_listing | PASS passed | 0.315s | test_4_agent_orchestration_staging.py |
| test_orchestration_workflow_states | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_agent_communication_patterns | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_orchestration_error_scenarios | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_multi_agent_coordination_metrics | PASS passed | 0.003s | test_4_agent_orchestration_staging.py |
| test_basic_functionality | PASS passed | 0.305s | test_5_response_streaming_staging.py |
| test_streaming_protocols | PASS passed | 0.000s | test_5_response_streaming_staging.py |
| test_chunk_handling | PASS passed | 0.000s | test_5_response_streaming_staging.py |
| test_streaming_performance_metrics | PASS passed | 0.000s | test_5_response_streaming_staging.py |
| test_backpressure_handling | PASS passed | 0.000s | test_5_response_streaming_staging.py |
| test_stream_recovery | PASS passed | 0.000s | test_5_response_streaming_staging.py |
| test_basic_functionality | PASS passed | 0.311s | test_6_failure_recovery_staging.py |
| test_failure_detection | PASS passed | 0.000s | test_6_failure_recovery_staging.py |
| test_retry_strategies | PASS passed | 0.000s | test_6_failure_recovery_staging.py |
| test_circuit_breaker | PASS passed | 0.000s | test_6_failure_recovery_staging.py |
| test_graceful_degradation | PASS passed | 0.001s | test_6_failure_recovery_staging.py |
| test_recovery_metrics | PASS passed | 0.000s | test_6_failure_recovery_staging.py |
| test_basic_functionality | PASS passed | 0.318s | test_7_startup_resilience_staging.py |
| test_startup_sequence | PASS passed | 0.000s | test_7_startup_resilience_staging.py |
| test_dependency_validation | PASS passed | 0.000s | test_7_startup_resilience_staging.py |
| test_cold_start_performance | PASS passed | 0.000s | test_7_startup_resilience_staging.py |
| test_startup_failure_handling | PASS passed | 0.000s | test_7_startup_resilience_staging.py |
| test_health_check_endpoints | PASS passed | 0.319s | test_7_startup_resilience_staging.py |
| test_basic_functionality | PASS passed | 0.367s | test_8_lifecycle_events_staging.py |
| test_event_types | PASS passed | 0.000s | test_8_lifecycle_events_staging.py |
| test_event_sequencing | PASS passed | 0.000s | test_8_lifecycle_events_staging.py |
| test_event_metadata | PASS passed | 0.000s | test_8_lifecycle_events_staging.py |
| test_event_filtering | PASS passed | 0.000s | test_8_lifecycle_events_staging.py |
| test_event_persistence | PASS passed | 0.000s | test_8_lifecycle_events_staging.py |
| test_basic_functionality | PASS passed | 0.302s | test_9_coordination_staging.py |
| test_coordination_patterns | PASS passed | 0.000s | test_9_coordination_staging.py |
| test_task_distribution | PASS passed | 0.000s | test_9_coordination_staging.py |
| test_synchronization_primitives | PASS passed | 0.000s | test_9_coordination_staging.py |
| test_consensus_mechanisms | PASS passed | 0.000s | test_9_coordination_staging.py |
| test_coordination_metrics | PASS passed | 0.000s | test_9_coordination_staging.py |

## Failed Tests Details

### FAILED: test_websocket_connection
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.413s
- **Error:** ..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:73: in test_websocket_connection
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await s...

### FAILED: test_websocket_event_flow_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 0.405s
- **Error:** ..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:139: in test_websocket_event_flow_real
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    a...

### FAILED: test_concurrent_websocket_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_1_websocket_events_staging.py
- **Duration:** 1.842s
- **Error:** ..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:247: in test_concurrent_websocket_real
    results = await asyncio.gather(*tasks)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:221: in test_connection
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await s...

### FAILED: test_real_agent_pipeline_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 0.331s
- **Error:** ..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_3_agent_pipeline_staging.py:204: in test_real_agent_pipeline_execution
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
   ...

### FAILED: test_real_agent_lifecycle_monitoring
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 1.072s
- **Error:** ..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_3_agent_pipeline_staging.py:357: in test_real_agent_lifecycle_monitoring
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
 ...

### FAILED: test_real_pipeline_error_handling
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 1.008s
- **Error:** ..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_3_agent_pipeline_staging.py:450: in test_real_pipeline_error_handling
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    ...

## Pytest Output Format

```
test_10_critical_path_staging.py::test_basic_functionality PASSED
test_10_critical_path_staging.py::test_critical_api_endpoints PASSED
test_10_critical_path_staging.py::test_end_to_end_message_flow PASSED
test_10_critical_path_staging.py::test_critical_performance_targets PASSED
test_10_critical_path_staging.py::test_critical_error_handling PASSED
test_10_critical_path_staging.py::test_business_critical_features PASSED
test_1_websocket_events_staging.py::test_health_check PASSED
test_1_websocket_events_staging.py::test_websocket_connection FAILED
test_1_websocket_events_staging.py::test_api_endpoints_for_agents PASSED
test_1_websocket_events_staging.py::test_websocket_event_flow_real FAILED
test_1_websocket_events_staging.py::test_concurrent_websocket_real FAILED
test_2_message_flow_staging.py::test_message_endpoints PASSED
test_2_message_flow_staging.py::test_real_message_api_endpoints PASSED
test_2_message_flow_staging.py::test_real_websocket_message_flow PASSED
test_2_message_flow_staging.py::test_real_thread_management PASSED
test_2_message_flow_staging.py::test_real_error_handling_flow PASSED
test_3_agent_pipeline_staging.py::test_real_agent_discovery PASSED
test_3_agent_pipeline_staging.py::test_real_agent_configuration PASSED
test_3_agent_pipeline_staging.py::test_real_agent_pipeline_execution FAILED
test_3_agent_pipeline_staging.py::test_real_agent_lifecycle_monitoring FAILED
test_3_agent_pipeline_staging.py::test_real_pipeline_error_handling FAILED
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
test_6_failure_recovery_staging.py::test_retry_strategies PASSED
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

==================================================
52 passed, 6 failed in 44.62s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 1 | 3 | 25.0% |
| Agent | 8 | 6 | 2 | 75.0% |
| Performance | 3 | 3 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
