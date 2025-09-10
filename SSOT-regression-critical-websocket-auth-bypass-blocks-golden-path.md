# SSOT Regression: Critical WebSocket Auth Bypass Blocks Golden Path

**GitHub Issue:** [#223](https://github.com/netra-systems/netra-apex/issues/223)
**Priority:** CRITICAL - Golden Path Blocker
**Status:** Discovery Complete - Planning Tests

## Problem Summary

WebSocket authentication bypass in `user_context_extractor.py` blocks Golden Path AI response delivery, affecting $500K+ ARR chat functionality by violating UnifiedAuthInterface SSOT.

## Key SSOT Violations Discovered

### 🔴 CRITICAL: WebSocket JWT Bypass (Lines 193-196)
```python
# VIOLATION: Direct JWT decode bypassing UnifiedAuthInterface
payload = jwt.decode(
    access_token,
    verify_signature=False,  # ← SSOT VIOLATION
    options={"verify_signature": False}
)
```

### 🔴 CRITICAL: Fallback Auth Logic (Lines 265-324)
```python
# VIOLATION: Local JWT validation instead of UnifiedAuthInterface
decoded_token = jwt.decode(
    token,
    PUBLIC_KEY,
    algorithms=["RS256"]
)
```

## Golden Path Impact

1. **User Login Flow** - Inconsistent auth validation
2. **WebSocket Connection** - Auth bypass causes state mismatches  
3. **AI Response Delivery** - Blocked by auth failures

## Work Progress

### Step 0: SSOT Audit ✅ COMPLETE
- [x] Discovered 396 SSOT violations in UnifiedAuthInterface
- [x] Prioritized WebSocket auth bypass as most critical
- [x] Created GitHub issue #223
- [x] Created progress tracker (this file)

### Step 1: Discover and Plan Tests (NEXT)
- [ ] 1.1: Find existing tests protecting against auth SSOT violations
- [ ] 1.2: Plan test updates/creation for SSOT refactor validation

### Step 2: Execute Test Plan  
- [ ] Create/update SSOT validation tests
- [ ] Run tests (unit, integration non-docker, e2e staging only)

### Step 3: Plan SSOT Remediation
- [ ] Plan removal of WebSocket JWT bypass
- [ ] Plan UnifiedAuthInterface integration

### Step 4: Execute SSOT Remediation  
- [ ] Remove direct JWT operations
- [ ] Implement UnifiedAuthInterface calls
- [ ] Update fallback logic

### Step 5: Test Fix Loop
- [ ] Prove system stability maintained
- [ ] Fix any test failures
- [ ] Validate Golden Path unblocked

### Step 6: PR and Closure
- [ ] Create PR linking to issue #223
- [ ] Verify tests pass
- [ ] Close issue on merge

## Notes
- Focus on atomic changes maintaining system stability
- No Docker tests - unit, integration (non-docker), e2e staging only
- Must pass all existing tests before introducing changes