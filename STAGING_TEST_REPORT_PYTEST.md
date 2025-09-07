# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-07 00:28:49
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 28
- **Passed:** 28 (100.0%)
- **Failed:** 0 (0.0%)
- **Skipped:** 0
- **Duration:** 39.58 seconds
- **Pass Rate:** 100.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_health_check | PASS passed | 0.715s | test_1_websocket_events_staging.py |
| test_websocket_connection | PASS passed | 0.512s | test_1_websocket_events_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.616s | test_1_websocket_events_staging.py |
| test_websocket_event_flow_real | PASS passed | 0.493s | test_1_websocket_events_staging.py |
| test_concurrent_websocket_real | PASS passed | 3.116s | test_1_websocket_events_staging.py |
| test_message_endpoints | PASS passed | 0.648s | test_2_message_flow_staging.py |
| test_real_message_api_endpoints | PASS passed | 0.962s | test_2_message_flow_staging.py |
| test_real_websocket_message_flow | PASS passed | 0.430s | test_2_message_flow_staging.py |
| test_real_thread_management | PASS passed | 0.597s | test_2_message_flow_staging.py |
| test_real_error_handling_flow | PASS passed | 1.175s | test_2_message_flow_staging.py |
| test_real_agent_discovery | PASS passed | 0.761s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.809s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | PASS passed | 0.466s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | PASS passed | 1.171s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | PASS passed | 1.070s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 3.887s | test_3_agent_pipeline_staging.py |
| test_basic_functionality | PASS passed | 0.491s | test_4_agent_orchestration_staging.py |
| test_agent_discovery_and_listing | PASS passed | 0.382s | test_4_agent_orchestration_staging.py |
| test_orchestration_workflow_states | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_agent_communication_patterns | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_orchestration_error_scenarios | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_multi_agent_coordination_metrics | PASS passed | 0.001s | test_4_agent_orchestration_staging.py |
| test_basic_functionality | PASS passed | 0.398s | test_5_response_streaming_staging.py |
| test_streaming_protocols | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_chunk_handling | PASS passed | 0.000s | test_5_response_streaming_staging.py |
| test_streaming_performance_metrics | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_backpressure_handling | PASS passed | 0.001s | test_5_response_streaming_staging.py |
| test_stream_recovery | PASS passed | 0.000s | test_5_response_streaming_staging.py |

## Pytest Output Format

```
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

==================================================
28 passed, 0 failed in 39.58s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 4 | 4 | 0 | 100.0% |
| Agent | 8 | 8 | 0 | 100.0% |
| Performance | 1 | 1 | 0 | 100.0% |

---
*Report generated by pytest-staging framework v1.0*
