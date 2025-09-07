# Top 100 E2E Staging Tests - Execution Report

**Generated:** 2025-09-07 08:22:54
**Environment:** Staging - https://netra-backend-staging-pnovr5vsba-uc.a.run.app
**Test Framework:** Pytest unknown

## Executive Summary

- **Total Tests:** 62
- **Passed:** 52
- **Failed:** 6
- **Skipped:** 0
- **Duration:** 44.60 seconds
- **Pass Rate:** 83.9%

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
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_websocket_connection FAILED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_api_endpoints_for_agents PASSED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_websocket_event_flow_real FAILED [0.00s]
tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_concurrent_websocket_real FAILED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_message_endpoints PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_real_message_api_endpoints PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_real_websocket_message_flow PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_real_thread_management PASSED [0.00s]
tests/e2e/staging/test_2_message_flow_staging.py::TestMessageFlowStaging::test_real_error_handling_flow PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_agent_discovery PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_agent_configuration PASSED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_agent_pipeline_execution FAILED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_agent_lifecycle_monitoring FAILED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_pipeline_error_handling FAILED [0.00s]
tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_pipeline_metrics PASSED [0.00s]
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
tests/e2e/staging/test_6_failure_recovery_staging.py::TestFailureRecoveryStaging::test_retry_strategies PASSED [0.00s]
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

============================================================
52 passed, 6 failed in 44.60s
```

## Results by Priority

### [NORMAL] Priority

**Results:** 52/62 passed, 6 failed

| Test | Result | Duration |
|------|--------|----------|
| test_basic_functionality | [PASS] passed | 0.000s |
| test_critical_api_endpoints | [PASS] passed | 0.000s |
| test_end_to_end_message_flow | [PASS] passed | 0.000s |
| test_critical_performance_targets | [PASS] passed | 0.000s |
| test_critical_error_handling | [PASS] passed | 0.000s |
| test_business_critical_features | [PASS] passed | 0.000s |
| test_health_check | [PASS] passed | 0.000s |
| test_websocket_connection | [FAIL] failed | 0.000s |
| test_api_endpoints_for_agents | [PASS] passed | 0.000s |
| test_websocket_event_flow_real | [FAIL] failed | 0.000s |
| test_concurrent_websocket_real | [FAIL] failed | 0.000s |
| test_message_endpoints | [PASS] passed | 0.000s |
| test_real_message_api_endpoints | [PASS] passed | 0.000s |
| test_real_websocket_message_flow | [PASS] passed | 0.000s |
| test_real_thread_management | [PASS] passed | 0.000s |
| test_real_error_handling_flow | [PASS] passed | 0.000s |
| test_real_agent_discovery | [PASS] passed | 0.000s |
| test_real_agent_configuration | [PASS] passed | 0.000s |
| test_real_agent_pipeline_execution | [FAIL] failed | 0.000s |
| test_real_agent_lifecycle_monitoring | [FAIL] failed | 0.000s |
| test_real_pipeline_error_handling | [FAIL] failed | 0.000s |
| test_real_pipeline_metrics | [PASS] passed | 0.000s |
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
| test_retry_strategies | [PASS] passed | 0.000s |
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
| test_001_basic_optimization_agent_flow | [SKIP] error | 0.000s |
| test_002_multi_turn_optimization_conversation | [SKIP] error | 0.000s |
| test_003_concurrent_user_isolation | [SKIP] error | 0.000s |
| test_004_realtime_agent_status_events | [SKIP] error | 0.000s |

## Failed Test Details

### [FAILED] tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_websocket_connection

**Error:**
```
..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:73: in test_websocket_connection
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:114: in handshake
    raise self.protocol.handshake_exc
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:325: in parse
    self.process_response(response)
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:142: in process_response
    raise InvalidStatus(response)
E   websockets.exceptions.InvalidStatus: server reje...
```

### [FAILED] tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_websocket_event_flow_real

**Error:**
```
..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:139: in test_websocket_event_flow_real
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:114: in handshake
    raise self.protocol.handshake_exc
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:325: in parse
    self.process_response(response)
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:142: in process_response
    raise InvalidStatus(response)
E   websockets.exceptions.InvalidStatus: serve...
```

### [FAILED] tests/e2e/staging/test_1_websocket_events_staging.py::TestWebSocketEventsStaging::test_concurrent_websocket_real

**Error:**
```
..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:247: in test_concurrent_websocket_real
    results = await asyncio.gather(*tasks)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_1_websocket_events_staging.py:221: in test_connection
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:114: in handshake
    raise self.protocol.handshake_exc
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:325: in parse
    self.process_response(response)
C:\Users\antho\AppData\Roaming\Python\Pytho...
```

### [FAILED] tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_agent_pipeline_execution

**Error:**
```
..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_3_agent_pipeline_staging.py:204: in test_real_agent_pipeline_execution
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:114: in handshake
    raise self.protocol.handshake_exc
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:325: in parse
    self.process_response(response)
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:142: in process_response
    raise InvalidStatus(response)
E   websockets.exceptions.InvalidStatus: ser...
```

### [FAILED] tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_agent_lifecycle_monitoring

**Error:**
```
..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_3_agent_pipeline_staging.py:357: in test_real_agent_lifecycle_monitoring
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:114: in handshake
    raise self.protocol.handshake_exc
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:325: in parse
    self.process_response(response)
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:142: in process_response
    raise InvalidStatus(response)
E   websockets.exceptions.InvalidStatus: s...
```

### [FAILED] tests/e2e/staging/test_3_agent_pipeline_staging.py::TestAgentPipelineStaging::test_real_pipeline_error_handling

**Error:**
```
..\staging_test_base.py:224: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
test_3_agent_pipeline_staging.py:450: in test_real_pipeline_error_handling
    async with websockets.connect(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:543: in __await_impl__
    await self.connection.handshake(
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\client.py:114: in handshake
    raise self.protocol.handshake_exc
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:325: in parse
    self.process_response(response)
C:\Users\antho\AppData\Roaming\Python\Python312\site-packages\websockets\client.py:142: in process_response
    raise InvalidStatus(response)
E   websockets.exceptions.InvalidStatus: serv...
```

## Test Coverage Analysis

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 10 | 7 | 3 | 70.0% |
| Agent | 15 | 10 | 3 | 66.7% |
| Message | 6 | 6 | 0 | 100.0% |
| Error | 4 | 3 | 1 | 75.0% |
| Performance | 3 | 3 | 0 | 100.0% |

## Environment Information

- **Python Version:** unknown
- **Platform:** unknown

## Recommendations

[WARNING] **System needs attention** - Pass rate is between 80-95%

### Priority Actions:


---
*Report generated by Top 100 E2E Test Framework*
