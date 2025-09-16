# HOTFIX: Production WebSocket async/await pattern violations

## Emergency Production Issue - P0 CRITICAL

**Parent Issue**: #1184 - WebSocket Manager await error
**Business Impact**: Golden Path user flow interruption ($500K+ ARR)
**Timeline**: 24-48 hours

## Problem Summary

Production logs show ongoing `object _UnifiedWebSocketManagerImplementation can't be used in 'await' expression` errors despite documented resolution of issue #1184.

**Error Location**:
- `netra_backend.app.routes.websocket_ssot:1651`
- `netra_backend.app.routes.websocket_ssot:954`

**Frequency**: Multiple occurrences per hour in staging environment

## Root Cause

Incorrect async/await pattern usage in production code:

```python
# INCORRECT (causing failures)
manager = await get_websocket_manager(user_context=ctx)

# CORRECT (should be used)
manager = get_websocket_manager(user_context=ctx)
# OR
manager = await get_websocket_manager_async(user_context=ctx)
```

## Immediate Actions Required

### 1. Production Code Audit
- [ ] Scan all files for `await get_websocket_manager()` patterns
- [ ] Identify specific line numbers and usage contexts
- [ ] Document current vs. correct patterns

### 2. Emergency Fix Implementation
- [ ] Replace incorrect `await get_websocket_manager()` calls
- [ ] Use appropriate sync/async patterns based on context
- [ ] Test fixes in staging before production deployment

### 3. Validation
- [ ] Deploy to staging environment
- [ ] Monitor GCP logs for error elimination
- [ ] Run Golden Path user flow validation
- [ ] Confirm WebSocket communication stability

## Acceptance Criteria

- [ ] Zero occurrences of `can't be used in 'await' expression` errors in GCP logs
- [ ] Golden Path user flow works end-to-end (users login → get AI responses)
- [ ] WebSocket communication functions normally in staging
- [ ] Production deployment ready with validated fix

## Files to Investigate

Primary focus areas:
- `netra_backend/app/routes/websocket_ssot.py` (lines 1651, 954)
- `netra_backend/app/websocket_core/manager.py`
- Any files using `get_websocket_manager()` function

## Testing Strategy

### Before Fix
- [ ] Reproduce error in staging environment
- [ ] Document exact error conditions

### After Fix
- [ ] Verify error elimination in staging logs
- [ ] Run WebSocket integration tests
- [ ] Execute Golden Path end-to-end test

## Risk Assessment

**Low Risk**: Focused code pattern fix with clear before/after validation
**High Impact**: Direct resolution of production stability issue

## Related Issues

- Parent: #1184 (WebSocket Manager await error)
- See: Master Plan document `MASTER_PLAN_1184_20250116.md`

## Definition of Done

- [ ] All `await get_websocket_manager()` patterns identified and fixed
- [ ] Staging environment shows zero related errors for 24+ hours
- [ ] Golden Path functionality validated in staging
- [ ] Production deployment plan approved
- [ ] Documentation updated with fix details

**Labels**: `bug`, `priority:critical`, `websocket`, `golden-path`