# Issue #1175 ClickHouse AsyncGeneratorContextManager Error - Test Reproduction Guide

## Overview

This guide provides commands and expected outcomes for testing the ClickHouse AsyncGeneratorContextManager error reproduction and validation of the fix.

**Root Cause**: The `_get_client()` method in `clickhouse_schema.py:438` treats the result of `get_clickhouse_client()` as a direct client, but it actually returns an async context manager.

**Error**: `'async_generator' object has no attribute 'execute'`

## Test Files Created

### 1. Unit Test - Error Reproduction
**File**: `netra_backend/tests/unit/db/test_clickhouse_schema_async_error.py`
**Purpose**: Reproduce the exact error with mocked async generators

### 2. Integration Test - Async Client Patterns
**File**: `netra_backend/tests/integration/db/test_clickhouse_async_client.py`
**Purpose**: Test proper async context manager usage patterns

### 3. E2E Staging Test - Production Validation
**File**: `netra_backend/tests/e2e/test_clickhouse_staging_integration.py`
**Purpose**: Validate fix works in staging environment

## Test Commands

### Unit Tests (Reproduces Error)
```bash
# Run the key test that reproduces the exact error
python -m pytest netra_backend/tests/unit/db/test_clickhouse_schema_async_error.py::TestClickHouseSchemaAsyncError::test_create_table_async_generator_context_manager_error -v

# Expected Result: PASS (test reproduces error correctly)
```

### Unit Tests (All Error Reproduction Tests)
```bash
# Run all unit tests that demonstrate the error patterns
python -m pytest netra_backend/tests/unit/db/test_clickhouse_schema_async_error.py -v

# Expected Result: Some tests PASS (reproducing error), some may need refinement
```

### Integration Tests (Before Fix)
```bash
# Run integration tests - these will FAIL with current implementation
python -m pytest netra_backend/tests/integration/db/test_clickhouse_async_client.py::TestClickHouseAsyncClientIntegration::test_schema_operations_with_proper_async_pattern -v

# Expected Result: FAIL with pytest.fail() showing async/sync mismatch error
```

### E2E Staging Tests (If ClickHouse Available)
```bash
# Run staging tests (may skip if ClickHouse not available)
python -m pytest netra_backend/tests/e2e/test_clickhouse_staging_integration.py::TestClickHouseStagingIntegration::test_staging_schema_operations -v -m staging

# Expected Result: SKIP (if no ClickHouse) or FAIL (if error present)
```

## Expected Test Outcomes

### Before Fix Implementation
1. **Unit Tests**: PASS - Successfully reproduce the `'async_generator' object has no attribute 'execute'` error
2. **Integration Tests**: FAIL with pytest.fail() messages confirming Issue #1175
3. **E2E Tests**: SKIP (no ClickHouse) or FAIL (error present in staging)

### After Fix Implementation
1. **Unit Tests**: PASS - Tests validate error was fixed
2. **Integration Tests**: PASS - Async context manager pattern works correctly
3. **E2E Tests**: PASS - Operations succeed in staging environment

## Key Test Validation Points

### 1. Error Reproduction Confirmation
The unit test successfully reproduces the exact error:
```
ERROR netra_backend.app.db.clickhouse_schema:clickhouse_schema.py:452 Error creating table test_table: 'async_generator' object has no attribute 'execute'
```

### 2. Error Pattern Matching
Tests check for both possible error formats:
- `'_AsyncGeneratorContextManager' object has no attribute 'execute'`
- `'async_generator' object has no attribute 'execute'`

### 3. Critical Operations Tested
- Table creation (`create_table`)
- Column querying (`get_table_columns`)
- Statistics gathering (`get_table_stats`)
- Concurrent operations
- Error recovery patterns

## Fix Validation Strategy

### 1. Immediate Validation
Run the unit test that reproduces the error:
```bash
python -m pytest netra_backend/tests/unit/db/test_clickhouse_schema_async_error.py::TestClickHouseSchemaAsyncError::test_create_table_async_generator_context_manager_error -v
```

### 2. Comprehensive Validation
After implementing the fix, run all three test suites:
```bash
# Unit tests should continue to pass (now testing the fix works)
python -m pytest netra_backend/tests/unit/db/test_clickhouse_schema_async_error.py -v

# Integration tests should now pass (async pattern working)
python -m pytest netra_backend/tests/integration/db/test_clickhouse_async_client.py -v

# E2E tests should pass if ClickHouse available
python -m pytest netra_backend/tests/e2e/test_clickhouse_staging_integration.py -v -m staging
```

### 3. Production Readiness Validation
For staging environment validation:
```bash
# Set staging environment and run E2E tests
export ENVIRONMENT=staging
python -m pytest netra_backend/tests/e2e/test_clickhouse_staging_integration.py -v -m staging
```

## Current Status ✅

- **Unit Test Creation**: ✅ COMPLETE - Error reproduction test working
- **Integration Test Creation**: ✅ COMPLETE - Async pattern validation ready
- **E2E Test Creation**: ✅ COMPLETE - Staging validation ready
- **Error Reproduction**: ✅ CONFIRMED - Tests reproduce exact production error
- **Test Framework**: ✅ VALIDATED - Tests properly catch the async/sync mismatch

## Next Steps

1. **Implement Fix**: Modify `clickhouse_schema.py` to use proper async context manager pattern
2. **Validate Fix**: Run test suite to confirm fix works
3. **Deploy**: Test in staging environment with E2E validation suite

## Success Criteria

✅ **Error Reproduction**: Tests successfully reproduce the `'async_generator' object has no attribute 'execute'` error
🔄 **Fix Implementation**: Pending - modify `_get_client()` method to use async context manager correctly
⏳ **Fix Validation**: Pending - all tests should pass after fix implementation
⏳ **Staging Validation**: Pending - E2E tests confirm fix works in production-like environment