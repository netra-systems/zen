## Problem
ClickHouse integration tests are failing due to missing required positional arguments for dependency injection.

## Error Details
Multiple test methods are failing with TypeError:
- missing 1 required positional argument: 'clickhouse_client'
- missing 1 required positional argument: 'schema_manager'

## Affected Tests
**Files:**
- netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py
- netra_backend/tests/clickhouse/test_clickhouse_schema_exception_types.py

**Failing Test Methods:**
- test_bulk_insert_errors_not_classified_by_cause
- test_cache_operations_lack_error_specificity
- test_invalid_query_lacks_specific_error_type
- test_performance_errors_not_classified_properly
- test_query_execution_lacks_connection_error_classification
- test_query_retry_logic_using_retryable_classification
- test_schema_operations_lack_diagnostic_context
- test_column_modification_uses_specific_error_types
- test_constraint_violation_provides_constraint_context
- test_engine_configuration_error_provides_engine_context

## Expected Behavior
Tests should properly inject required dependencies (clickhouse_client, schema_manager) via fixtures or dependency injection patterns.

## Impact
- Critical integration tests are failing
- Database functionality testing is compromised
- CI/CD pipeline may be affected

## Environment
- Python 3.13.7
- Test framework: pytest
- Platform: Windows

## Priority
This is a critical issue affecting database testing infrastructure and should be addressed promptly to maintain system stability and test coverage.

## Suggested Fix
Review dependency injection patterns in ClickHouse test suite and ensure proper fixture configuration for required parameters.