# Staging E2E Test Report - Pytest Results

**Generated:** 2025-09-14 10:48:45
**Environment:** Staging
**Test Framework:** Pytest

## Executive Summary

- **Total Tests:** 11
- **Passed:** 1 (9.1%)
- **Failed:** 10 (90.9%)
- **Skipped:** 0
- **Duration:** 23.42 seconds
- **Pass Rate:** 9.1%

## Test Results by Priority

### NORMAL Priority Tests

| Test Name | Status | Duration | File |
|-----------|--------|----------|------|
| test_staging_index_operation_workflow_error_classification_gap | FAIL failed | 0.000s | test_missing_exception_types_staging_e2e.py |
| test_staging_migration_deployment_workflow_error_gap | FAIL failed | 0.000s | test_missing_exception_types_staging_e2e.py |
| test_staging_dependency_validation_workflow_error_gap | FAIL failed | 0.000s | test_missing_exception_types_staging_e2e.py |
| test_staging_data_validation_workflow_constraint_error_gap | FAIL failed | 0.000s | test_missing_exception_types_staging_e2e.py |
| test_staging_environment_setup_engine_configuration_error_gap | FAIL failed | 0.001s | test_missing_exception_types_staging_e2e.py |
| test_staging_end_to_end_error_classification_workflow_gaps | FAIL failed | 0.000s | test_missing_exception_types_staging_e2e.py |
| test_staging_event_validator_endpoint_consistency | PASS passed | 0.000s | test_golden_path_event_validation.py |
| test_staging_websocket_event_validation_golden_path | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_agent_execution_event_validation_consistency | FAIL failed | 0.000s | test_golden_path_event_validation.py |
| test_staging_deployment_validator_readiness | FAIL failed | 0.019s | test_golden_path_event_validation.py |
| test_malformed_event_recovery_mechanisms | FAIL failed | 0.000s | test_validation_inconsistency_recovery.py |

## Failed Tests Details

### FAILED: test_staging_index_operation_workflow_error_classification_gap
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py:115: in test_staging_index_operation_workflow_error_classification_gap
    await self.schema_manager.create_table("staging_analytics_events", staging_analytics_table)
netra_backend\app\db\clickhouse_schema.py:465: in create_table
    raise classified_error from e
netra_backend\app\db\clickhouse_schema.py:451: in create_table
    await asyncio.get_event_loop().run_in_executor(
C:\Program Files\Python313\Lib\concurrent\future...

### FAILED: test_staging_migration_deployment_workflow_error_gap
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py:194: in test_staging_migration_deployment_workflow_error_gap
    await self.schema_manager.create_table("staging_user_profiles", staging_base_table)
netra_backend\app\db\clickhouse_schema.py:465: in create_table
    raise classified_error from e
netra_backend\app\db\clickhouse_schema.py:451: in create_table
    await asyncio.get_event_loop().run_in_executor(
C:\Program Files\Python313\Lib\concurrent\futures\thread.py:59: in...

### FAILED: test_staging_dependency_validation_workflow_error_gap
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py:268: in test_staging_dependency_validation_workflow_error_gap
    await self.schema_manager.create_table("staging_raw_events", staging_events_table)
netra_backend\app\db\clickhouse_schema.py:465: in create_table
    raise classified_error from e
netra_backend\app\db\clickhouse_schema.py:451: in create_table
    await asyncio.get_event_loop().run_in_executor(
C:\Program Files\Python313\Lib\concurrent\futures\thread.py:59: in...

### FAILED: test_staging_data_validation_workflow_constraint_error_gap
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py:349: in test_staging_data_validation_workflow_constraint_error_gap
    await self.schema_manager.create_table("staging_user_data_quality", staging_quality_table)
netra_backend\app\db\clickhouse_schema.py:465: in create_table
    raise classified_error from e
netra_backend\app\db\clickhouse_schema.py:451: in create_table
    await asyncio.get_event_loop().run_in_executor(
C:\Program Files\Python313\Lib\concurrent\futures\thr...

### FAILED: test_staging_environment_setup_engine_configuration_error_gap
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py
- **Duration:** 0.001s
- **Error:** tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py:434: in test_staging_environment_setup_engine_configuration_error_gap
    with pytest.raises(AssertionError, match="Should be EngineConfigurationError for staging"):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE <class 'AssertionError'>...

### FAILED: test_staging_end_to_end_error_classification_workflow_gaps
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\clickhouse\test_missing_exception_types_staging_e2e.py:513: in test_staging_end_to_end_error_classification_workflow_gaps
    with pytest.raises(AssertionError, match=f"{expected_type} should not exist yet"):
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   Failed: DID NOT RAISE <class 'AssertionError'>...

### FAILED: test_staging_websocket_event_validation_golden_path
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:474: in test_staging_websocket_event_validation_golden_path
    self.fail(
    ^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'fail'...

### FAILED: test_staging_agent_execution_event_validation_consistency
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:577: in test_staging_agent_execution_event_validation_consistency
    self.fail(
    ^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'fail'...

### FAILED: test_staging_deployment_validator_readiness
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py
- **Duration:** 0.019s
- **Error:** tests\e2e\staging\event_validator_ssot\test_golden_path_event_validation.py:702: in test_staging_deployment_validator_readiness
    self.fail(
    ^^^^^^^^^
E   AttributeError: 'TestGoldenPathEventValidationStaging' object has no attribute 'fail'...

### FAILED: test_malformed_event_recovery_mechanisms
- **File:** C:\GitHub\netra-apex\tests\e2e\staging\event_validator_ssot\test_validation_inconsistency_recovery.py
- **Duration:** 0.000s
- **Error:** tests\e2e\staging\event_validator_ssot\test_validation_inconsistency_recovery.py:267: in test_malformed_event_recovery_mechanisms
    scenario = self.recovery_scenarios[0]  # malformed_event_recovery
               ^^^^^^^^^^^^^^^^^^^^^^^
E   AttributeError: 'TestValidationInconsistencyRecovery' object has no attribute 'recovery_scenarios'...

## Pytest Output Format

```
test_missing_exception_types_staging_e2e.py::test_staging_index_operation_workflow_error_classification_gap FAILED
test_missing_exception_types_staging_e2e.py::test_staging_migration_deployment_workflow_error_gap FAILED
test_missing_exception_types_staging_e2e.py::test_staging_dependency_validation_workflow_error_gap FAILED
test_missing_exception_types_staging_e2e.py::test_staging_data_validation_workflow_constraint_error_gap FAILED
test_missing_exception_types_staging_e2e.py::test_staging_environment_setup_engine_configuration_error_gap FAILED
test_missing_exception_types_staging_e2e.py::test_staging_end_to_end_error_classification_workflow_gaps FAILED
test_golden_path_event_validation.py::test_staging_event_validator_endpoint_consistency PASSED
test_golden_path_event_validation.py::test_staging_websocket_event_validation_golden_path FAILED
test_golden_path_event_validation.py::test_staging_agent_execution_event_validation_consistency FAILED
test_golden_path_event_validation.py::test_staging_deployment_validator_readiness FAILED
test_validation_inconsistency_recovery.py::test_malformed_event_recovery_mechanisms FAILED

==================================================
1 passed, 10 failed in 23.42s
```

## Test Coverage Matrix

| Category | Total | Passed | Failed | Coverage |
|----------|-------|--------|--------|----------|
| WebSocket | 1 | 0 | 1 | 0.0% |
| Agent | 1 | 0 | 1 | 0.0% |

---
*Report generated by pytest-staging framework v1.0*
