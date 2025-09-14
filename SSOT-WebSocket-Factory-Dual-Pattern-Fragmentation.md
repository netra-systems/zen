# SSOT-WebSocket-Factory-Dual-Pattern-Fragmentation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1126
**Status:** DISCOVERY COMPLETE
**Priority:** P0 (Mission Critical)
**Business Impact:** $500K+ ARR Golden Path blocked

## Issue Summary
Deprecated `WebSocketManagerFactory` still exists alongside SSOT `get_websocket_manager()`, creating dual patterns that cause race conditions in WebSocket event delivery and user isolation failures.

## Critical Evidence
- **File**: `/netra_backend/app/websocket_core/websocket_manager_factory.py`
- **Lines**: 544-586 (WebSocketManagerFactory class)
- **Exports**: Lines 573-574 in `__all__`
- **Affected Files**: 15+ files importing deprecated patterns
- **Test Failure**: `test_issue_1100_websocket_ssot_mission_critical.py` lines 147-150

## SSOT Violation Details
- **SSOT Path**: `get_websocket_manager()` from `websocket_manager.py`
- **Violation Path**: `create_websocket_manager()` from `websocket_manager_factory.py`
- **Impact**: Dual creation patterns undermine user context isolation

## Remediation Plan
1. ✅ **Step 0**: SSOT audit complete - critical issue identified
2. 🔄 **Step 1**: Discover and plan tests
3. ⏳ **Step 2**: Execute test plan (20% new SSOT tests)
4. ⏳ **Step 3**: Plan SSOT remediation  
5. ⏳ **Step 4**: Execute remediation
6. ⏳ **Step 5**: Test fix loop
7. ⏳ **Step 6**: PR and closure

## Files to Update
### Primary Target
- `netra_backend/app/websocket_core/websocket_manager_factory.py` (remove deprecated class)

### Secondary Targets (imports to update)
- Search for: `from netra_backend.app.websocket_core.websocket_manager_factory import`
- Replace with canonical SSOT imports

## Test Strategy
- **Existing**: Mission critical test already exists and failing
- **New**: Create SSOT validation test for factory pattern consistency
- **Validation**: Ensure WebSocket event delivery remains stable

## Success Criteria
- [ ] `WebSocketManagerFactory` class removed
- [ ] Deprecated exports removed from `__all__`
- [ ] All importing files updated to SSOT patterns
- [ ] Mission critical tests pass
- [ ] No regression in WebSocket event delivery
- [ ] Golden Path user flow operational

## Progress Log
- **2025-09-14 16:30**: Issue discovered and GitHub issue created
- **Next**: Discover existing tests and plan new SSOT validation tests