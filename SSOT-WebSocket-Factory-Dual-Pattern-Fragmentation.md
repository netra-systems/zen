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

## Test Discovery Results (Step 1.1)
### Existing Tests Found
- **Mission Critical**: 1 failing test (`test_issue_1100_websocket_ssot_mission_critical.py`)
- **Unit Tests**: ~150 files (14/14 passing basic tests, 6/8 failing SSOT tests)
- **Integration Tests**: ~100 files (mostly SKIPPED awaiting environment)
- **E2E/Staging**: ~50 files (operational via staging)

### Key Finding
**30+ files still import deprecated factory** including production code:
- `netra_backend/app/services/unified_authentication_service.py`
- `netra_backend/app/websocket_core/handlers.py` (5 imports)

## Test Plan (Step 1.2)
### 4 New SSOT Validation Tests (20% of work)
1. **Factory Pattern Validation Test**: Ensure only SSOT `get_websocket_manager()` accessible
2. **Import Consistency Test**: Validate no deprecated imports exist  
3. **WebSocket Instance Isolation Test**: Ensure user context isolation with SSOT
4. **Event Delivery Consistency Test**: Validate all 5 WebSocket events work via SSOT

### Test Strategy
- **20% new tests** (4 SSOT validation tests)
- **60% existing test validation** (ensure they pass after fix)
- **20% broken test fixes** (repair affected tests)

## Test Implementation Results (Step 2)
### 4 New SSOT Validation Tests Created ✅
1. ✅ **Factory Pattern Validation**: `tests/unit/websocket_ssot/test_websocket_factory_ssot_enforcement.py`
2. ✅ **Import Consistency**: `tests/unit/websocket_ssot/test_websocket_import_path_consistency.py`  
3. ✅ **User Isolation**: `tests/unit/websocket_ssot/test_websocket_user_isolation_ssot.py`
4. ✅ **Event Delivery**: `tests/integration/websocket_ssot/test_websocket_events_ssot_delivery.py`

### Test Results (As Expected)
- **Total Tests**: 23 tests across 4 files
- **FAILED**: 5 tests (proving dual pattern fragmentation exists)
- **PASSED**: 18 tests (SSOT patterns work correctly)

### Key Failing Tests (Proving Issue)
- `test_deprecated_websocket_manager_factory_class_not_accessible` - WebSocketManagerFactory still accessible  
- `test_deprecated_import_paths_raise_errors` - Deprecated imports still work
- `test_no_duplicate_websocket_manager_implementations` - Duplicate implementations exist

## Progress Log
- **2025-09-14 16:30**: Issue discovered and GitHub issue created
- **2025-09-14 16:45**: Step 1 complete - Test discovery and planning done
- **2025-09-14 16:55**: Step 2 complete - 4 SSOT validation tests created and validated
- **2025-01-14 14:30**: **Step 4 complete** - Comprehensive test suite executed, dual pattern issue confirmed
- **2025-01-14 14:45**: **Step 5 complete** - Detailed remediation plan created
- **Next**: Execute SSOT remediation (atomic fix: remove 2 deprecated exports from __all__)