# Golden Path E2E Tests: Async and Deprecation Warning Cleanup

## Issue Summary
During test execution, multiple warnings are being generated that indicate technical debt and potential issues in our test infrastructure. These warnings affect test output clarity and may indicate underlying async handling or import issues.

## Warning Categories Identified

### 1. RuntimeWarning: Coroutine Never Awaited
**Pattern:** `RuntimeWarning: coroutine was never awaited`
**Impact:** Indicates async functions being called without await, potentially causing resource leaks or unexpected behavior
**Root Cause:** Test methods calling async functions without proper awaiting

**Affected Areas:**
- E2E test files with async test methods
- Files found with `async def test_` pattern:
  - `/tests/e2e/staging/test_issue_1278_golden_path_validation.py`
  - `/tests/e2e/integration/test_staging_complete_e2e.py`
  - `/tests/e2e/integration/test_staging_websocket_messaging.py`
  - And ~17 additional test files

### 2. DeprecationWarning: logging_config Module Deprecated
**Pattern:** `DeprecationWarning: netra_backend.app.logging_config is deprecated`
**Impact:** Using deprecated logging imports instead of SSOT unified logging
**Root Cause:** Legacy imports that haven't been migrated to SSOT pattern

**Affected Files (200+ instances found):**
- Test files importing `from netra_backend.app.logging_config import central_logger`
- Service files still using legacy logging imports
- Helper modules using deprecated logging patterns

**Current Deprecation Message:**
```
"netra_backend.app.logging_config is deprecated. 
Use 'from shared.logging.unified_logging_ssot import get_logger' instead."
```

### 3. DeprecationWarning: Test Return Values
**Pattern:** `DeprecationWarning: It is deprecated to return a value that is not None from a test case`
**Impact:** Test functions returning values instead of using assertions
**Root Cause:** Test methods returning status/results instead of proper pytest patterns

## Business Impact
- **GOLDEN PATH RISK:** Warning noise can mask real test failures
- **DEVELOPER PRODUCTIVITY:** Cluttered test output reduces debugging efficiency 
- **SSOT COMPLIANCE:** Deprecated imports violate architecture standards
- **TECHNICAL DEBT:** Async handling issues may indicate race conditions

## Proposed Solution

### Phase 1: Logging SSOT Migration (High Priority)
1. **Automated Migration Script:** Create script to replace all deprecated logging imports
   ```python
   # FROM (deprecated):
   from netra_backend.app.logging_config import central_logger
   
   # TO (SSOT):
   from shared.logging.unified_logging_ssot import get_logger
   logger = get_logger(__name__)
   ```

2. **Validation:** Ensure all 200+ affected files are migrated
3. **Testing:** Verify logging still works correctly across all services

### Phase 2: Async Test Cleanup (Medium Priority)
1. **Audit async test methods:** Review all files with `async def test_` patterns
2. **Fix unawaited coroutines:** Ensure all async calls are properly awaited
3. **Test framework compliance:** Verify proper async test execution patterns

### Phase 3: Test Return Value Cleanup (Low Priority)
1. **Identify test methods returning values:** Search for `return` statements in test functions
2. **Convert to assertions:** Replace return values with proper pytest assertions
3. **Validation:** Ensure test behavior is preserved

## Success Criteria
- [ ] Zero deprecation warnings during test execution
- [ ] Zero RuntimeWarning messages about unawaited coroutines
- [ ] All tests use SSOT logging patterns
- [ ] Clean test output for improved debugging experience
- [ ] No regression in test functionality

## Files Requiring Attention

### High Priority (SSOT Logging Migration)
- All files importing `from netra_backend.app.logging_config`
- Test framework files using deprecated logging
- Service files with legacy logging patterns

### Medium Priority (Async Handling)
- `/tests/e2e/staging/test_issue_1278_golden_path_validation.py`
- `/tests/e2e/integration/test_staging_complete_e2e.py`
- Other async test files identified

### Low Priority (Test Return Values)
- Test files with return statements (to be identified in detailed analysis)

## Labels
- `technical-debt`
- `testing`
- `golden-path`
- `ssot-compliance`
- `warnings-cleanup`

## Priority
**Medium** - Affects test clarity and SSOT compliance but doesn't block Golden Path functionality

## Estimated Effort
- Phase 1: 4-6 hours (automated script + validation)
- Phase 2: 2-3 hours (async test review)
- Phase 3: 1-2 hours (test return value cleanup)

**Total: 7-11 hours**

---

*This issue supports the Golden Path mission by ensuring clean, maintainable test infrastructure that doesn't obscure real issues with warning noise.*