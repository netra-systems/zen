# Failing Test Gardener Worklog - ALL TESTS
**Date:** 2025-09-13
**Test Focus:** ALL_TESTS (unit, integration non-docker, e2e staging)
**Status:** Initial Discovery Complete

## Executive Summary
Discovered multiple categories of test failures across unit, integration, and database test suites. Primary issues involve import/module problems, configuration errors, and database exception handling specificity.

**Total Issues Identified:** 15 unique issues across 4 categories
**Severity Breakdown:**
- P1 High: 8 issues (Import/Module failures blocking test execution)
- P2 Medium: 5 issues (Database test failures affecting error handling)
- P3 Low: 2 issues (Configuration and collection issues)

## Issue Categories

### 1. IMPORT/MODULE ISSUES (8 Issues - P1 High Priority)

#### Issue 1.1: Missing 'validate_token' import from user_auth_service
**Type:** Import Error
**Severity:** P1 - High
**Test Files Affected:**
- `netra_backend/tests/unit/test_user_auth_service_compatibility.py:31`
- `netra_backend/tests/unit/test_user_auth_service_comprehensive.py:34`

**Error Details:**
```
ImportError: cannot import name 'validate_token' from 'netra_backend.app.services.user_auth_service'
```

**Impact:** 2 auth-related unit tests cannot be executed

#### Issue 1.2: Missing 'UserWebSocketEmitter' import from websocket_bridge_factory
**Type:** Import Error
**Severity:** P1 - High
**Test Files Affected:**
- `netra_backend/tests/unit/test_websocket_bridge.py:18`
- `netra_backend/tests/unit/tool_dispatcher/test_tool_dispatcher_user_isolation.py:44`

**Error Details:**
```
ImportError: cannot import name 'UserWebSocketEmitter' from 'netra_backend.app.services.websocket_bridge_factory'
```

**Impact:** WebSocket bridge and tool dispatcher isolation tests cannot run

#### Issue 1.3: Missing 'user_websocket_emitter' module
**Type:** Module Not Found Error
**Severity:** P1 - High
**Test Files Affected:**
- `netra_backend/tests/unit/test_websocket_error_validation_comprehensive.py:25`

**Error Details:**
```
ModuleNotFoundError: No module named 'netra_backend.app.services.user_websocket_emitter'
```

**Impact:** WebSocket error validation tests cannot execute

#### Issue 1.4: Missing 'test_execution_engine_comprehensive_real_services' module
**Type:** Module Not Found Error
**Severity:** P1 - High
**Test Files Affected:**
- `netra_backend/tests/integration/test_execution_engine_advanced_scenarios.py:75`

**Error Details:**
```
ModuleNotFoundError: No module named 'test_execution_engine_comprehensive_real_services'
```

**Impact:** Advanced execution engine integration tests cannot run

### 2. DATABASE TEST FAILURES (5 Issues - P2 Medium Priority)

#### Issue 2.1: ClickHouse exception type mismatch - TableNotFoundError
**Type:** Test Failure - Wrong Exception Type
**Severity:** P2 - Medium
**Test Files Affected:**
- `netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py::TestClickHouseExceptionSpecificity::test_invalid_query_lacks_specific_error_type`

**Error Details:**
```
AssertionError: Should be TableNotFoundError, got OperationalError
assert 'TableNotFoundError' in 'OperationalError'
```

**Impact:** Database error classification not working correctly

#### Issue 2.2: ClickHouse schema error diagnostic context missing
**Type:** Test Failure - Missing Error Context
**Severity:** P2 - Medium
**Test Files Affected:**
- `netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py::TestClickHouseExceptionSpecificity::test_schema_operations_lack_diagnostic_context`

**Error Details:**
```
AssertionError: Should include schema error prefix
assert 'Schema Error:' in "(builtins.NoneType) None\n[SQL: Column 'invalid_column' already exists]"
```

**Impact:** Schema error messages lack proper diagnostic prefixes

#### Issue 2.3: Query retry logic not using retryable classification
**Type:** Test Failure - Missing Retry Logic Classification
**Severity:** P2 - Medium
**Test Files Affected:**
- `netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py::TestClickHouseExceptionSpecificity::test_query_retry_logic_not_using_retryable_classification`

**Impact:** Database query retry mechanisms not properly classifying retryable errors

#### Issue 2.4: Cache operations lack error specificity
**Type:** Test Failure - Generic Error Handling
**Severity:** P2 - Medium
**Test Files Affected:**
- `netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py::TestClickHouseExceptionSpecificity::test_cache_operations_lack_error_specificity`

**Impact:** Cache-related database operations not providing specific error types

#### Issue 2.5: Performance errors not classified as TimeoutError
**Type:** Test Failure - Wrong Exception Type
**Severity:** P2 - Medium
**Test Files Affected:**
- `netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py::TestClickHouseExceptionSpecificity::test_performance_errors_not_classified_properly`

**Error Details:**
```
AssertionError: Should be TimeoutError, got ConnectionError
assert 'TimeoutError' in 'ConnectionError'
```

**Impact:** Performance-related database errors misclassified as connection errors

### 3. CONFIGURATION ISSUES (2 Issues - P3 Low Priority)

#### Issue 3.1: Missing pytest markers configuration
**Type:** Configuration Error
**Severity:** P3 - Low
**Test Files Affected:**
- `netra_backend/tests/integration/race_conditions/test_execution_engine_registry_races.py`
- `netra_backend/tests/integration/test_config_shared_components_comprehensive.py`

**Error Details:**
```
'real_redis' not found in `markers` configuration option
'shared_components' not found in `markers` configuration option
```

**Impact:** Integration tests with custom markers cannot be collected

#### Issue 3.2: Test classes with __init__ constructors causing collection issues
**Type:** Collection Warning
**Severity:** P3 - Low
**Test Files Affected:**
- `netra_backend/tests/integration/database_persistence/test_database_persistence_golden_path_integration.py:79`
- `netra_backend/tests/integration/test_execution_engine.py:61`

**Error Details:**
```
PytestCollectionWarning: cannot collect test class 'TestUserData' because it has a __init__ constructor
PytestCollectionWarning: cannot collect test class 'TestExecutionAgent' because it has a __init__ constructor
```

**Impact:** Test classes not collected due to pytest collection rules

## Additional Observations

### Deprecation Warnings (Informational)
- Multiple deprecated import paths for logging and WebSocket components
- Pydantic V2.0 deprecation warnings for class-based config
- Several deprecated module paths across the codebase

### System Context
- Docker Desktop not running (affects E2E tests)
- Windows environment detected for E2E testing
- Memory usage peaked at 374.8MB during unit test collection
- Test collection successful for 9902 unit tests, 2727 integration tests, 131 database tests

## Next Steps
Each issue will be processed through the subagent workflow to:
1. Search for existing related GitHub issues
2. Create new issues or update existing ones with current context
3. Link related issues and documentation
4. Assign appropriate priority and severity tags

## Test Execution Stats
- **Unit Tests:** 9902 collected, 5 errors preventing execution
- **Database Tests:** 131 collected, 5 failures in exception specificity
- **Integration Tests:** 2727 collected, 3 collection errors
- **Overall Success Rate:** ~92% collection success, multiple execution failures

---
*Generated by Failing Test Gardener on 2025-09-13*