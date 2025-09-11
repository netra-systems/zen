# SessionMetrics SSOT Bug Test Suite

## Overview

This document describes the comprehensive test suite created to expose and validate the SessionMetrics SSOT violation that causes `AttributeError` in `request_scoped_session_factory.py` line 383-385.

## The Bug

**Location**: `netra_backend/app/database/request_scoped_session_factory.py` lines 383-385

**Issue**: The error handling code tries to access:
- `session_metrics.last_activity` (should be `last_activity_at`)
- `session_metrics.operations_count` (doesn't exist)
- `session_metrics.errors` (should be `error_count`)

**Root Cause**: Two `SessionMetrics` classes exist with different field names:
1. `netra_backend.app.database.request_scoped_session_factory.SessionMetrics`
2. `shared.session_management.user_session_manager.SessionMetrics`

## Test Files Created

### 1. Unit Test: `netra_backend/tests/unit/test_session_metrics_ssot_validation.py`

**Purpose**: Validate SessionMetrics interfaces and reproduce exact field access errors.

**Key Tests**:
- `test_session_metrics_field_access_consistency()` - Reproduces exact AttributeError
- `test_request_scoped_session_factory_error_field_access()` - Simulates exact bug location
- `test_session_metrics_interface_compatibility()` - Compares class interfaces
- `test_session_metrics_purpose_mismatch()` - Identifies architectural issues

**Run Command**:
```bash
python -m pytest netra_backend/tests/unit/test_session_metrics_ssot_validation.py -v -s
```

### 2. Integration Test: `netra_backend/tests/integration/test_request_scoped_session_factory_error_paths.py`

**Purpose**: Test database error scenarios with real services that trigger the bug.

**Key Tests**:
- `test_database_connection_error_triggers_ssot_bug()` - Forces database errors
- `test_session_timeout_error_path()` - Tests timeout scenarios 
- `test_session_factory_pool_exhaustion_error()` - Tests pool exhaustion
- `test_session_metrics_creation_and_error_logging()` - Direct error logging test

**Requirements**: 
- Real PostgreSQL connection (test environment)
- Uses `LightweightServicesFixture` for real database

**Run Command**:
```bash
python -m pytest netra_backend/tests/integration/test_request_scoped_session_factory_error_paths.py -v -s --real-services
```

### 3. SSOT Detection Test: `tests/integration/test_ssot_class_duplication_detection.py`

**Purpose**: Scan codebase for duplicate class names and SSOT violations.

**Key Tests**:
- `test_scan_for_duplicate_class_names()` - Scans entire codebase for duplicates
- `test_session_metrics_specific_ssot_violation()` - Specific SessionMetrics analysis
- `test_critical_class_pattern_violations()` - Tests critical patterns
- `test_import_path_consistency()` - Validates import conflicts

**Features**:
- AST-based Python file parsing
- Field and method interface comparison
- Comprehensive SSOT violation reporting

**Run Command**:
```bash
python -m pytest tests/integration/test_ssot_class_duplication_detection.py -v -s
```

### 4. E2E Auth Test: `tests/e2e/test_session_metrics_auth_integration.py`

**Purpose**: Test session metrics with real authentication and WebSocket connections.

**Key Tests**:
- `test_websocket_auth_session_metrics_integration()` - WebSocket auth + session metrics
- `test_multi_user_concurrent_session_metrics()` - Concurrent user sessions
- `test_session_metrics_database_auth_error_integration()` - Database auth errors
- `test_session_cleanup_auth_scenarios()` - Session cleanup scenarios

**Requirements**:
- Real authentication via `test_framework/ssot/e2e_auth_helper.py`
- Real WebSocket connections
- Real database services

**Run Command**:
```bash
python -m pytest tests/e2e/test_session_metrics_auth_integration.py -v -s --real-services --authenticated
```

## Expected Test Behavior

All tests are **DESIGNED TO FAIL** when the SSOT violation exists:

### Unit Tests
- **PASS**: When they successfully reproduce the AttributeError (proving the bug exists)
- **FAIL**: When they don't reproduce the bug (indicating it may be fixed)

### Integration Tests  
- **FAIL**: When database errors trigger SessionMetrics field access AttributeError
- **PASS**: When database errors are handled without field access bugs

### SSOT Detection Tests
- **FAIL**: When duplicate SessionMetrics classes are found with different interfaces
- **PASS**: When only single SessionMetrics class exists (SSOT compliant)

### E2E Auth Tests
- **FAIL**: When real user sessions trigger AttributeError in session handling
- **PASS**: When user sessions complete without SessionMetrics field bugs

## Running the Complete Test Suite

### Quick Validation (Unit Tests Only)
```bash
python -m pytest netra_backend/tests/unit/test_session_metrics_ssot_validation.py -v -s --tb=short
```

### Full Integration Testing
```bash
# Requires real services
python -m pytest \
  netra_backend/tests/unit/test_session_metrics_ssot_validation.py \
  netra_backend/tests/integration/test_request_scoped_session_factory_error_paths.py \
  tests/integration/test_ssot_class_duplication_detection.py \
  -v -s --real-services --tb=short
```

### Complete E2E Testing
```bash
# Requires real services + authentication
python -m pytest \
  netra_backend/tests/unit/test_session_metrics_ssot_validation.py \
  netra_backend/tests/integration/test_request_scoped_session_factory_error_paths.py \
  tests/integration/test_ssot_class_duplication_detection.py \
  tests/e2e/test_session_metrics_auth_integration.py \
  -v -s --real-services --authenticated --tb=short
```

## Using Unified Test Runner

The tests integrate with the unified test runner:

```bash
# Run all session metrics tests
python tests/unified_test_runner.py \
  --pattern "*session_metrics*" \
  --real-services \
  --categories unit integration e2e

# Focus on specific test type
python tests/unified_test_runner.py \
  --pattern "*ssot_validation*" \
  --category unit \
  --fast-fail
```

## Test Framework Integration

All tests follow CLAUDE.MD patterns:

- **SSOT Compliance**: Uses `test_framework/ssot/` utilities
- **Real Services**: No mocks in integration/E2E tests
- **Authentication**: All E2E tests use real auth via `e2e_auth_helper.py`
- **Absolute Imports**: All imports use absolute paths
- **Error Handling**: Tests designed to fail hard to expose real issues

## Interpreting Results

### When Tests FAIL (Expected)
This proves the SessionMetrics SSOT violation exists and causes real runtime errors.

### When Tests PASS
This indicates:
1. The SSOT violation has been fixed, OR
2. The tests aren't triggering the right error conditions, OR  
3. The bug manifests differently than expected

### Key Error Messages to Look For

- `AttributeError: 'SessionMetrics' object has no attribute 'last_activity'`
- `AttributeError: 'SessionMetrics' object has no attribute 'operations_count'` 
- `AttributeError: 'SessionMetrics' object has no attribute 'errors'`
- Any error containing both "SessionMetrics" and "has no attribute"

## Next Steps

1. **Run Tests**: Execute the test suite to confirm SSOT violation exists
2. **Analyze Results**: Review which specific field access patterns fail
3. **Fix SSOT Violation**: Consolidate SessionMetrics classes with consistent interface
4. **Validate Fix**: Re-run tests to ensure they pass after fix
5. **Update Architecture**: Document the corrected SSOT implementation

## Related Documentation

- **[CLAUDE.MD](CLAUDE.MD)** - SSOT principles and architectural requirements
- **[TEST_CREATION_GUIDE.md](reports/testing/TEST_CREATION_GUIDE.md)** - Test framework patterns
- **[SSOT Learnings](SPEC/learnings/)** - Historical SSOT violation patterns
- **[User Context Architecture](reports/archived/USER_CONTEXT_ARCHITECTURE.md)** - Factory patterns and isolation