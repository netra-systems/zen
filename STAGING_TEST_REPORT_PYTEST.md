# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-08 08:58:57
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 19
- **Passed:** 12 (63.2%)
- **Failed:** 7 (36.8%)
- **Skipped:** 0
- **Duration:** 30.48 seconds
- **Pass Rate:** 63.2%

## Test Results by Priority

### CRITICAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_001_unified_data_agent_real_execution | FAIL failed | 0.676s | test_real_agent_execution_staging.py |
| test_002_optimization_agent_real_execution | FAIL failed | 0.614s | test_real_agent_execution_staging.py |
| test_003_multi_agent_coordination_real | FAIL failed | 0.569s | test_real_agent_execution_staging.py |
| test_004_concurrent_user_isolation | PASS passed | 1.439s | test_real_agent_execution_staging.py |
| test_005_error_recovery_resilience | FAIL failed | 0.615s | test_real_agent_execution_staging.py |
| test_006_performance_benchmarks | FAIL failed | 5.443s | test_real_agent_execution_staging.py |
| test_007_business_value_validation | FAIL failed | 1.873s | test_real_agent_execution_staging.py |

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_real_agent_discovery | PASS passed | 0.700s | test_3_agent_pipeline_staging.py |
| test_real_agent_configuration | PASS passed | 0.604s | test_3_agent_pipeline_staging.py |
| test_real_agent_pipeline_execution | FAIL failed | 3.632s | test_3_agent_pipeline_staging.py |
| test_real_agent_lifecycle_monitoring | PASS passed | 1.622s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_error_handling | PASS passed | 1.242s | test_3_agent_pipeline_staging.py |
| test_real_pipeline_metrics | PASS passed | 3.482s | test_3_agent_pipeline_staging.py |
| test_basic_functionality | PASS passed | 0.329s | test_4_agent_orchestration_staging.py |
| test_agent_discovery_and_listing | PASS passed | 0.340s | test_4_agent_orchestration_staging.py |
| test_orchestration_workflow_states | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_agent_communication_patterns | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_orchestration_error_scenarios | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |
| test_multi_agent_coordination_metrics | PASS passed | 0.000s | test_4_agent_orchestration_staging.py |

## Failed Tests Details

### FAILED: test_real_agent_pipeline_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_3_agent_pipeline_staging.py
- **Duration:** 3.632s
- **Error:** ..\..\..\..\miniconda3\Lib\asyncio\tasks.py:520: in wait_for
    return await fut
           ^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\connection.py:303: in recv
    return await self.recv_messages.get(decode)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
..\..\..\..\AppData\Roaming\Python\Python312\site-packages\websockets\asyncio\messages.py:159: in get
    frame = await self.frames.get(not self.closed)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^...

### FAILED: test_001_unified_data_agent_real_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.676s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:505: in test_001_unified_data_agent_real_execution
    assert has_content, "Agent should provide some content or analysis (staging may use mock responses)"
E   AssertionError: Agent should provide some content or analysis (staging may use mock responses)
E   assert False

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_real_agent_execution_staging.py:465: in test_001_unified_data_agent_real_executio...

### FAILED: test_002_optimization_agent_real_execution
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.614s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:541: in test_002_optimization_agent_real_execution
    assert len(tool_events) > 0, "Optimization should use analysis tools"
E   AssertionError: Optimization should use analysis tools
E   assert 0 > 0
E    +  where 0 = len([])

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_real_agent_execution_staging.py:514: in test_002_optimization_agent_real_execution
    async with validator.create_authenticat...

### FAILED: test_003_multi_agent_coordination_real
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.569s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:590: in test_003_multi_agent_coordination_real
    assert quality_score >= min_quality, f"Multi-agent coordination quality insufficient: {quality_score:.2f} (staging threshold: {min_quality})"
E   AssertionError: Multi-agent coordination quality insufficient: 0.00 (staging threshold: 0.2)
E   assert 0 >= 0.2

During handling of the above exception, another exception occurred:
tests\e2e\staging\test_real_agent_execution_staging.py:556: in tes...

### FAILED: test_005_error_recovery_resilience
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 0.615s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:682: in test_005_error_recovery_resilience
    assert len(error_events) > 0 or len(events) == 0, \
E   AssertionError: Should handle invalid requests gracefully with error events or no events
E   assert (0 > 0 or 1 == 0)
E    +  where 0 = len([])
E    +  and   1 = len([{'details': {'environment': 'staging', 'error_code': 'VALIDATION_FAILED', 'failure_context': {'auth_headers': {'authorization_present': True, 'authorization_preview': 'Bearer ...

### FAILED: test_006_performance_benchmarks
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 5.443s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:778: in test_006_performance_benchmarks
    assert avg_quality >= PERFORMANCE_THRESHOLDS["min_response_quality_score"], \
E   AssertionError: Quality SLA violation: 0.00 < 0.7
E   assert 0 >= 0.7...

### FAILED: test_007_business_value_validation
- **File:** C:\Users\antho\OneDrive\Desktop\Netra\netra-core-generation-1\tests\e2e\staging\test_real_agent_execution_staging.py
- **Duration:** 1.873s
- **Error:** tests\e2e\staging\test_real_agent_execution_staging.py:869: in test_007_business_value_validation
    assert high_value_scenarios >= total_scenarios * 0.7, \
E   AssertionError: Insufficient high-value scenarios: 0/3
E   assert 0 >= (3 * 0.7)...

## Pytest Output Format

```
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
test_real_agent_execution_staging.py::test_001_unified_data_agent_real_execution FAILED
test_real_agent_execution_staging.py::test_002_optimization_agent_real_execution FAILED
test_real_agent_execution_staging.py::test_003_multi_agent_coordination_real FAILED
test_real_agent_execution_staging.py::test_004_concurrent_user_isolation PASSED
test_real_agent_execution_staging.py::test_005_error_recovery_resilience FAILED
test_real_agent_execution_staging.py::test_006_performance_benchmarks FAILED
test_real_agent_execution_staging.py::test_007_business_value_validation FAILED

==================================================
12 passed, 7 failed in 30.48s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| Agent | 10 | 6 | 4 | 60.0% |
| Performance | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
