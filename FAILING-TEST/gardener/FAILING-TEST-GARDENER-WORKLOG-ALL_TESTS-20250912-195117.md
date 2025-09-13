# FAILING-TEST-GARDENER-WORKLOG-ALL_TESTS-20250912-195117

## Executive Summary

**Test Run Date:** 2025-09-12 19:51:17  
**Environment:** staging  
**Test Categories:** unit, integration, e2e, database, api, frontend  
**Overall Status:** FAILED  
**Total Duration:** 55.78s  

### Category Results:
- ✅ frontend: PASSED (2.14s)  
- ❌ database: FAILED (4.25s) - 10 test failures
- ❌ unit: FAILED (28.27s) - Collection errors  
- ❌ api: FAILED (2.96s)  
- ❌ integration: FAILED (10.53s)  
- ❌ e2e: FAILED (7.61s)  

## Discovered Issues for SNST Processing

### Issue 1: Database ClickHouse Exception Specificity Failures
**Category:** failing-test-regression-p1-clickhouse-exception-handling  
**Severity:** P1 - High (Database layer critical infrastructure)  
**Files Affected:**
- `netra_backend/tests/clickhouse/test_clickhouse_exception_specificity.py`
- `netra_backend/tests/clickhouse/test_clickhouse_schema_exception_types.py`

**Failing Tests (10 total):**
1. `test_query_execution_lacks_connection_error_classification` - Failed: DID NOT RAISE TransactionConnectionError
2. `test_invalid_query_lacks_specific_error_type` - Failed: DID NOT RAISE Exception
3. `test_schema_operations_lack_diagnostic_context` - Failed: DID NOT RAISE Exception
4. `test_bulk_insert_errors_not_classified_by_cause` - AttributeError: 'ClickHouseService' object has no attribute 'insert_data'
5. `test_query_retry_logic_not_using_retryable_classification` - AssertionError: Should be classified as ConnectionError
6. `test_cache_operations_lack_error_specificity` - AttributeError: missing '_cache' attribute
7. `test_performance_errors_not_classified_properly` - Failed: DID NOT RAISE Exception
8. `test_table_creation_lacks_specific_error_types` - AssertionError: Should be TableCreationError, got AttributeError
9. `test_column_modification_lacks_error_specificity` - AssertionError: Should be ColumnModificationError, got AttributeError
10. `test_index_creation_lacks_specific_error_handling` - AssertionError: Should be IndexCreationError, got AttributeError

**Root Cause:** ClickHouseService class missing expected methods and proper exception classification system.

### Issue 2: Unit Test Collection Import Error - Auth Startup Validator
**Category:** uncollectable-test-regression-p1-auth-import-missing  
**Severity:** P1 - High (Blocking test collection)  
**File:** `netra_backend/tests/unit/test_auth_startup_validation_integration_validation.py:25`  
**Error:** `ImportError: cannot import name 'validate_auth_at_startup' from 'netra_backend.app.core.auth_startup_validator'`  
**Impact:** Prevents unit test collection, interrupts test suite execution

### Issue 3: Auth Service Secret Loader Marker Configuration Error
**Category:** uncollectable-test-new-p2-marker-config  
**Severity:** P2 - Medium (Test configuration issue)  
**File:** `auth_service/tests/unit/test_secret_loader_comprehensive.py`  
**Error:** `'secret_loader' not found in markers configuration option`  
**Impact:** Test collection failure in auth service

### Issue 4: Missing User Execution Engine Function  
**Category:** failing-test-regression-p2-execution-engine-missing  
**Severity:** P2 - Medium (Skipped tests, not blocking)  
**File:** `netra_backend/tests/unit/agents/test_execution_engine_comprehensive.py:73`  
**Error:** `cannot import name 'create_request_scoped_engine' from 'netra_backend.app.agents.supervisor.user_execution_engine'`  
**Impact:** Execution engine tests skipped due to missing function

### Issue 5: Test Collection Warnings - Constructor Issues
**Category:** failing-test-new-p3-test-class-constructors  
**Severity:** P3 - Low (Warnings, not blocking)  
**Files:**
- `netra_backend/tests/unit/test_base_agent_comprehensive.py:49`
- `netra_backend/tests/unit/test_toolregistry_basemodel_filtering.py:33`
- Multiple WebSocket test files

**Pattern:** `PytestCollectionWarning: cannot collect test class 'TestXxx' because it has a __init__ constructor`  
**Impact:** Test classes not being collected due to constructor pattern

### Issue 6: Deprecation Warnings - Logging and Import Patterns
**Category:** failing-test-active-dev-p3-deprecation-cleanup  
**Severity:** P3 - Low (Technical debt)  
**Pattern:** Multiple deprecation warnings for:
- `shared.logging.unified_logger_factory` usage  
- WebSocket import paths  
- Pydantic class-based config  
- Environment detector usage  

### Issue 7: Missing Dependencies and Removed Modules
**Category:** failing-test-regression-p2-missing-dependencies  
**Severity:** P2 - Medium (Organizational debt)  
**Skipped Tests:**
- Cost limit enforcement  
- Error recovery integration  
- Security monitoring integration  
- State checkpoint session functionality  
- WebSocket ghost connections (functionality removed)

### Issue 8: Environment Configuration - Missing JWT_SECRET
**Category:** failing-test-regression-p1-environment-config  
**Severity:** P1 - High (Authentication critical)  
**Discovery:** Issue #463 reproduction test found `JWT_SECRET is missing (None)`  
**Impact:** WebSocket authentication failures in staging environment

## Next Steps

Each issue above requires processing through the SNST workflow:
1. Search for existing GitHub issues
2. Create new issue or update existing with priority tags (P0-P3)
3. Link related issues, PRs, and documentation
4. Update this worklog and commit/push safely

**Priority Processing Order:**
1. P1 issues (Database, Auth, Environment) - Critical business impact
2. P2 issues (Missing functions, Dependencies) - Moderate impact  
3. P3 issues (Warnings, Deprecations) - Technical debt cleanup

## Test Infrastructure Notes

- **Memory Usage:** Peak 416.8 MB during unit tests
- **Redis Libraries:** Not available - Redis fixtures failing
- **Docker:** Not initialized - Docker cleanup skipped
- **Environment:** Using staging database URL fallback
- **Total Test Files:** 5,602 syntax validation passed
- **Collection Success:** Despite errors, many tests still executable

## Related Documentation
- Test Report: `/Users/anthony/Desktop/netra-apex/test_reports/test_report_20250912_195117.json`
- SSOT Import Registry: `SSOT_IMPORT_REGISTRY.md`
- Test Execution Guide: `TEST_EXECUTION_GUIDE.md`