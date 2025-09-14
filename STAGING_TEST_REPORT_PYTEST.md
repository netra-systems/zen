# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-13 20:01:41
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 15
- **Passed:** 10 (66.7%)
- **Failed:** 5 (33.3%)
- **Skipped:** 0
- **Duration:** 31.02 seconds
- **Pass Rate:** 66.7%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_agent_execution_event_validation_consistency | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_agent_execution_traceability_impact | FAIL failed | 0.000s | test_id_consistency_e2e_staging.py |
| test_api_endpoints_for_agents | PASS passed | 0.503s | test_1_websocket_events_staging.py |
| test_real_agent_discovery | PASS passed | 0.733s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.557s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | FAIL failed | 0.720s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | FAIL failed | 1.812s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | FAIL failed | 1.264s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 3.443s | test_3_agent_pipeline_staging.py |
| test_basic_functionality | PASS passed | 0.282s | test_4_agent_orchestration_staging.py |
| test_agent_discovery_and_listing | PASS passed | 0.307s | test_4_agent_orchestration_staging.py |
| test_orchestration_workflow_states | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_agent_communication_patterns | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_orchestration_error_scenarios | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_multi_agent_coordination_metrics | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |

## Failed Tests Details

### FAILED: test_staging_agent_execution_event_validation_consistency
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:507: in test_staging_agent_execution_event_validation_consistency
    if not self.staging_base_url:
           ^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'staging_base_url'...

### FAILED: test_staging_agent_execution_traceability_impact
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\issue_803\test_id_consistency_e2e_staging.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\issue_803\test_id_consistency_e2e_staging.py:213: in test_staging_agent_execution_traceability_impact
    base_thread_counter = int(thread_id.split('_')[2])
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ValueError: invalid literal for int() with base 10: 'execution'...

### FAILED: test_real_agent_pipeline_execution
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 0.720s
- **Error:** tests\e2e\staging_test_base.py:322: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_3_agent_pipeline_staging.py:252: in test_real_agent_pipeline_execution
    async with websockets.connect(
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\client.py:543...

### FAILED: test_real_agent_lifecycle_monitoring
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 1.812s
- **Error:** tests\e2e\staging_test_base.py:322: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_3_agent_pipeline_staging.py:404: in test_real_agent_lifecycle_monitoring
    async with websockets.connect(
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\client.py:5...

### FAILED: test_real_pipeline_error_handling
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 1.264s
- **Error:** tests\e2e\staging_test_base.py:322: in wrapper
    return await func(*args, **kwargs)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests\e2e\staging\test_3_agent_pipeline_staging.py:498: in test_real_pipeline_error_handling
    async with websockets.connect(
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\client.py:587: in __aenter__
    return await self
           ^^^^^^^^^^
C:\Users\USER\AppData\Roaming\Python\Python313\site-packages\websockets\asyncio\client.py:543:...

## Pytest Output Format

```
test_golden_path_event_validation.py::test_staging_agent_execution_event_validation_consistency FAILED
test_id_consistency_e2e_staging.py::test_staging_agent_execution_traceability_impact FAILED
test_1_websocket_events_staging.py::test_api_endpoints_for_agents PASSED
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

==================================================
10 passed, 5 failed in 31.02s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Agent | 10 | 6 | 4 | 60.0% |

---
*Report generated by pytest-staging framework v1.0*
