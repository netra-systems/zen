## 📝 Test Plan for Issue #584

### Test Strategy Summary

I've created a comprehensive test plan to reproduce and validate the ID generation inconsistency fix. The plan focuses on non-Docker tests only.

### Test Categories

1. **SSOT Violation Detection Tests**
   - Detect bypassing of UnifiedIDManager
   - Validate consistent ID patterns
   - Test ID format validation

2. **Correlation Logic Tests**
   - Test thread_id extraction from run_id
   - Test WebSocket cleanup correlation failures
   - Test debugging/tracing correlation issues

3. **Remediation Validation Tests**
   - Test UnifiedIDManager methods work correctly
   - Validate consistent generation after fix
   - Test backward compatibility

### Test Files Plan

1. **Enhanced**: `tests/issue_584/test_demo_websocket_id_inconsistency.py` (existing - make more comprehensive)
2. **New**: `tests/integration/test_id_generation_ssot_compliance.py` (system-wide compliance)
3. **New**: `tests/unit/test_unified_id_manager_demo_compliance.py` (UnifiedIDManager compliance)

### Expected Behavior

- **Before Fix**: Tests should FAIL (demonstrating the problem)
- **After Fix**: Tests should PASS (proving the solution)

### Implementation Approach

1. Create failing tests that reproduce the exact issue
2. Fix demo_websocket.py to use UnifiedIDManager SSOT methods
3. Validate tests pass after remediation
4. Ensure no breaking changes to existing functionality

Starting test implementation now...