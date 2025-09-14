**Status:** Issue #926 TEST PLAN Complete - Auth Service Variable Scope Testing Strategy

## Test Plan Overview

Comprehensive test plan created for reproducing and validating the auth_service undefined variable issue affecting:
- Line 348: Shutdown function Redis cleanup
- Lines 665-667: Health endpoint session management check
- Root cause: Variable scope mismatch between import (line 249 lifespan function) and usage locations

## Test Strategy

**3-Phase Approach:** Unit → Integration → E2E (Staging GCP)

### Phase 1: Unit Tests
- **File:** `auth_service/tests/unit/test_auth_service_variable_scope.py`
- **Focus:** Reproduce NameError in isolated function scopes
- **Expected:** Tests 2-3 FAIL before fix (shutdown and health endpoint access)

### Phase 2: Integration Tests
- **File:** `auth_service/tests/integration/test_auth_service_initialization_sequence.py`
- **Focus:** Real service lifecycle with auth_service variable scope issues
- **Expected:** Shutdown and health endpoint integration tests FAIL before fix

### Phase 3: E2E Staging Tests
- **File:** `tests/e2e/staging/test_auth_service_variable_scope_e2e.py`
- **Focus:** Real Cloud Run deployment health endpoint failures
- **Expected:** Health endpoints return 500 errors due to undefined variable

## Business Value Protection

✅ **$500K+ ARR Golden Path:** Tests validate auth flow unaffected by variable scope fixes
✅ **Real Services Only:** Following CLAUDE.md directive - no mocks in integration/E2E
✅ **SSOT Compliance:** Using unified test infrastructure patterns

## Failure Modes to Reproduce

**Before Fix:**
- `NameError: name 'auth_service' is not defined` in shutdown function
- Health endpoint `/health/auth` session management check fails
- Service monitoring reports inaccurate status

**After Fix:**
- All variable scope tests pass
- Health endpoints return accurate service status
- Graceful shutdown completes without errors

## Test Deliverables

1. **Unit Test Suite:** Isolated variable scope testing
2. **Integration Test Suite:** Real service lifecycle validation
3. **E2E Test Suite:** Staging deployment validation
4. **Business Impact Assessment:** Golden Path functionality protection

**Next:** Implement failing unit tests first, progress through integration and E2E phases to validate complete fix

**Full Test Plan:** [issue_926_test_plan.md](./issue_926_test_plan.md)