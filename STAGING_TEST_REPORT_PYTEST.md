# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-14 10:50:20
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 15
- **Passed:** 12 (80.0%)
- **Failed:** 3 (20.0%)
- **Skipped:** 0
- **Duration:** 47.61 seconds
- **Pass Rate:** 80.0%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_agent_execution_event_validation_consistency | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_agent_execution_traceability_impact | FAIL failed | 0.000s | test_id_consistency_e2e_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.695s | test_1_websocket_events_staging.py |
| test_real_agent_discovery | PASS passed | 0.816s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.618s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | FAIL failed | 15.895s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | PASS passed | 1.492s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | PASS passed | 1.861s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 3.495s | test_3_agent_pipeline_staging.py |
| test_basic_functionality | PASS passed | 0.360s | test_4_agent_orchestration_staging.py |
| test_agent_discovery_and_listing | PASS passed | 0.341s | test_4_agent_orchestration_staging.py |
| test_orchestration_workflow_states | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_agent_communication_patterns | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_orchestration_error_scenarios | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_multi_agent_coordination_metrics | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |

## Failed Tests Details

### FAILED: test_staging_agent_execution_event_validation_consistency
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:577: in test_staging_agent_execution_event_validation_consistency
    self.fail(
    ^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'fail'...

### FAILED: test_staging_agent_execution_traceability_impact
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\issue_803\test_id_consistency_e2e_staging.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\issue_803\test_id_consistency_e2e_staging.py:213: in test_staging_agent_execution_traceability_impact
    base_thread_counter = int(thread_id.split('_')[2])
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ValueError: invalid literal for int() with base 10: 'execution'...

### FAILED: test_real_agent_pipeline_execution
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 15.895s
- **Error:** C:\Program Files\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\connection.py:303: in recv
    return await self.recv_messages.get(decode)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\messages.py:159: in get
    frame = await self.frames.get(not self.closed)
            ^^^^^^^^^^^^^^^^^^^^^^^...

## Pytest Output Format

```
test_golden_path_event_validation.py::test_staging_agent_execution_event_validation_consistency FAILED
test_id_consistency_e2e_staging.py::test_staging_agent_execution_traceability_impact FAILED
test_1_websocket_events_staging.py::test_api_endpoints_for_agents PASSED
test_3_agent_pipeline_staging.py::test_real_agent_discovery PASSED
test_3_agent_pipeline_staging.py::test_real_agent_configuration PASSED
test_3_agent_pipeline_staging.py::test_real_agent_pipeline_execution FAILED
test_3_agent_pipeline_staging.py::test_real_agent_lifecycle_monitoring PASSED
test_3_agent_pipeline_staging.py::test_real_pipeline_error_handling PASSED
test_3_agent_pipeline_staging.py::test_real_pipeline_metrics PASSED
test_4_agent_orchestration_staging.py::test_basic_functionality PASSED
test_4_agent_orchestration_staging.py::test_agent_discovery_and_listing PASSED
test_4_agent_orchestration_staging.py::test_orchestration_workflow_states PASSED
test_4_agent_orchestration_staging.py::test_agent_communication_patterns PASSED
test_4_agent_orchestration_staging.py::test_orchestration_error_scenarios PASSED
test_4_agent_orchestration_staging.py::test_multi_agent_coordination_metrics PASSED

==================================================
12 passed, 3 failed in 47.61s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Agent | 10 | 7 | 3 | 70.0% |

---
*Report generated by pytest-staging framework v1.0*
