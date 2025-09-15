# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-14 20:25:23
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 11
- **Passed:** 1 (9.1%)
- **Failed:** 10 (90.9%)
- **Skipped:** 0
- **Duration:** 21.06 seconds
- **Pass Rate:** 9.1%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_event_validator_endpoint_consistency | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_websocket_event_validation_golden_path | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_agent_execution_event_validation_consistency | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_deployment_validator_readiness | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_golden_path_auth_session_id_violation_staging_must_fail | PASS passed | 0.000s | test_golden_path_user_isolation_staging.py |
| test_golden_path_websocket_auth_isolation_staging_must_fail | FAIL failed | 0.000s | test_golden_path_user_isolation_staging.py |
| test_golden_path_concurrent_user_staging_must_fail | FAIL failed | 0.000s | test_golden_path_user_isolation_staging.py |
| test_golden_path_websocket_event_correlation_staging_must_fail | FAIL failed | 0.000s | test_golden_path_user_isolation_staging.py |
| test_golden_path_agent_orchestration_naming | FAIL failed | 0.000s | test_agent_orchestration_name_consistency_issue347.py |
| test_golden_path_execution_engine_factory_complete_user_flow_failures | FAIL failed | 0.000s | test_execution_engine_factory_884_golden_path.py |
| test_concurrent_golden_path_execution_scalability_failures | FAIL failed | 0.000s | test_execution_engine_factory_884_golden_path.py |

## Failed Tests Details

### FAILED: test_staging_event_validator_endpoint_consistency
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:132: in test_staging_event_validator_endpoint_consistency
    if not self.staging_base_url:
           ^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'staging_base_url'...

### FAILED: test_staging_websocket_event_validation_golden_path
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:177: in test_staging_websocket_event_validation_golden_path
    if not self.staging_websocket_url:
           ^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'staging_websocket_url'...

### FAILED: test_staging_agent_execution_event_validation_consistency
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:227: in test_staging_agent_execution_event_validation_consistency
    if not self.staging_base_url:
           ^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'staging_base_url'...

### FAILED: test_staging_deployment_validator_readiness
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:284: in test_staging_deployment_validator_readiness
    if not self.staging_base_url:
           ^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'staging_base_url'...

### FAILED: test_golden_path_websocket_auth_isolation_staging_must_fail
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py:111: in test_golden_path_websocket_auth_isolation_staging_must_fail
    self.websocket_connections.append(ws_connection)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathUserIsolationStaging' object has no attribute 'websocket_connections'

During handling of the above exception, another exception occurred:
tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py:146: in test_golden_path_w...

### FAILED: test_golden_path_concurrent_user_staging_must_fail
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py:179: in test_golden_path_concurrent_user_staging_must_fail
    self.websocket_connections.append(connection)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathUserIsolationStaging' object has no attribute 'websocket_connections'

During handling of the above exception, another exception occurred:
tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py:225: in test_golden_path_concurrent_us...

### FAILED: test_golden_path_websocket_event_correlation_staging_must_fail
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py:237: in test_golden_path_websocket_event_correlation_staging_must_fail
    self.websocket_connections.append(ws_connection)
    ^^^^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestGoldenPathUserIsolationStaging' object has no attribute 'websocket_connections'

During handling of the above exception, another exception occurred:
tests\e2e\staging\id_migration\test_golden_path_user_isolation_staging.py:298: in test_golden_pat...

### FAILED: test_golden_path_agent_orchestration_naming
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_agent_orchestration_name_consistency_issue347.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_agent_orchestration_name_consistency_issue347.py:108: in test_golden_path_agent_orchestration_naming
    user_context = self.staging_users["golden_path_user"]
                   ^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestAgentOrchestrationNameConsistencyE2E' object has no attribute 'staging_users'...

### FAILED: test_golden_path_execution_engine_factory_complete_user_flow_failures
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_execution_engine_factory_884_golden_path.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_execution_engine_factory_884_golden_path.py:174: in test_golden_path_execution_engine_factory_complete_user_flow_failures
    self.assertTrue(golden_path_results['overall_success'], f"GOLDEN PATH FAILURE: Golden Path did not complete successfully. Completed {golden_path_results['successful_stages']}/{golden_path_results['total_stages']} stages ({golden_path_results['completion_rate']:.1%}). Stage failures: {golden_path_stage_failures}. Factory coordination prevents complet...

### FAILED: test_concurrent_golden_path_execution_scalability_failures
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\test_execution_engine_factory_884_golden_path.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\test_execution_engine_factory_884_golden_path.py:245: in test_concurrent_golden_path_execution_scalability_failures
    self.assertLess(failure_rate, max_acceptable_failure_rate, f'HIGH GOLDEN PATH FAILURE RATE: {failure_rate:.1%} of concurrent Golden Path executions failed (threshold: {max_acceptable_failure_rate:.1%}). Failed: {len(failed_golden_paths)}, Total: {len(results)}. Factory scalability issues prevent reliable Golden Path execution.')
test_framework\ssot\base_test_c...

## Pytest Output Format

```
test_golden_path_event_validation.py::test_staging_event_validator_endpoint_consistency FAILED
test_golden_path_event_validation.py::test_staging_websocket_event_validation_golden_path FAILED
test_golden_path_event_validation.py::test_staging_agent_execution_event_validation_consistency FAILED
test_golden_path_event_validation.py::test_staging_deployment_validator_readiness FAILED
test_golden_path_user_isolation_staging.py::test_golden_path_auth_session_id_violation_staging_must_fail PASSED
test_golden_path_user_isolation_staging.py::test_golden_path_websocket_auth_isolation_staging_must_fail FAILED
test_golden_path_user_isolation_staging.py::test_golden_path_concurrent_user_staging_must_fail FAILED
test_golden_path_user_isolation_staging.py::test_golden_path_websocket_event_correlation_staging_must_fail FAILED
test_agent_orchestration_name_consistency_issue347.py::test_golden_path_agent_orchestration_naming FAILED
test_execution_engine_factory_884_golden_path.py::test_golden_path_execution_engine_factory_complete_user_flow_failures FAILED
test_execution_engine_factory_884_golden_path.py::test_concurrent_golden_path_execution_scalability_failures FAILED

==================================================
1 passed, 10 failed in 21.06s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 3 | 0 | 3 | 0.0% |
| Agent | 2 | 0 | 2 | 0.0% |
| Authentication | 2 | 1 | 1 | 50.0% |

---
*Report generated by pytest-staging framework v1.0*
