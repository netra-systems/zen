# SSOT-regression-direct-os-environ-access-in-testing-config

**GitHub Issue**: #828
**Status**: In Progress - Test Discovery Phase
**Priority**: P1 (High)
**Created**: 2025-09-13
**Last Updated**: 2025-09-13

## Issue Summary

Critical SSOT violation in testing configuration that violates IsolatedEnvironment patterns by directly accessing `os.environ.items()` in `NetraTestingConfig.__init__()`.

## Business Impact
- **Golden Path Protection**: Testing infrastructure reliability protects $500K+ ARR functionality
- **SSOT Compliance**: Maintains architectural consistency across testing systems
- **System Stability**: Ensures test environment isolation works correctly

## Technical Details

**File**: `netra_backend/app/schemas/config.py`
**Lines**: 1464-1466
**Violation**:
```python
# CRITICAL FIX: For test scenarios using patch.dict(os.environ), we need to
# merge isolated variables with os.environ, giving priority to os.environ
env_dict = env.as_dict()
for key, value in os.environ.items():  # ← DIRECT OS.ENVIRON ACCESS VIOLATION!
    if key not in env_dict or env_dict[key] != value:
        env_dict[key] = value
```

**Root Cause**: Direct `os.environ` access bypasses SSOT IsolatedEnvironment pattern

## Process Progress

### ✅ Step 0: SSOT AUDIT (Complete)
- [x] Discovered critical SSOT violation in testing config
- [x] Identified P1 priority violation blocking Golden Path testing reliability
- [x] Created GitHub issue #828
- [x] Created local progress tracker (this file)

### 🔄 Step 1: DISCOVER AND PLAN TEST (In Progress)
- [ ] Discover existing tests protecting against this SSOT violation
- [ ] Identify tests that validate IsolatedEnvironment usage in config
- [ ] Plan new tests to reproduce the SSOT violation
- [ ] Design tests for ideal SSOT-compliant state after fix

### ⏸️ Step 2: EXECUTE TEST PLAN (Pending)
- [ ] Create new SSOT validation tests
- [ ] Run tests to confirm violation detection
- [ ] Validate test framework without Docker dependency

### ⏸️ Step 3: PLAN REMEDIATION (Pending)
- [ ] Plan replacement of `os.environ.items()` with IsolatedEnvironment method
- [ ] Ensure test scenario compatibility maintained
- [ ] Design atomic fix that doesn't break existing functionality

### ⏸️ Step 4: EXECUTE REMEDIATION (Pending)
- [ ] Implement SSOT-compliant solution
- [ ] Maintain backward compatibility for test scenarios
- [ ] Update documentation if needed

### ⏸️ Step 5: TEST FIX LOOP (Pending)
- [ ] Run all existing tests to ensure no regressions
- [ ] Validate new SSOT tests pass
- [ ] Fix any breaking changes iteratively

### ⏸️ Step 6: PR AND CLOSURE (Pending)
- [ ] Create pull request with fix
- [ ] Link to issue #828 for auto-closure
- [ ] Validate all tests pass before merge

## Notes
- **ATOMIC SCOPE**: Focus only on fixing the direct os.environ access
- **SAFETY FIRST**: Ensure test scenario compatibility is preserved
- **SSOT COMPLIANCE**: All environment access must go through IsolatedEnvironment

## Next Actions
1. Spawn sub-agent to discover and plan tests for this SSOT violation
2. Focus on non-Docker test execution as specified in process requirements