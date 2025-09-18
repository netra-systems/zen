# SSOT-incomplete-migration-websocket-manager-consolidation

## Issue Summary
WebSocket Manager SSOT Consolidation Required - Three different manager implementations violate SSOT

## GitHub Issue
- Issue: To be created
- Link: Pending

## Current Status
- **Priority:** HIGH - $500K+ ARR risk
- **Phase:** Step 0 - Discovery Complete

## SSOT Violations Found

### 1. WebSocket Manager Triplication
**Files:**
- `/netra_backend/app/websocket_core/manager.py` - Compatibility layer
- `/netra_backend/app/websocket_core/unified_manager.py` - Core implementation  
- `/netra_backend/app/websocket_core/websocket_manager.py` - SSOT facade

**Issue:** Three different manager files exist when there should be ONE

### 2. Import Path Fragmentation
- Over 1,700+ files contain WebSocket manager references
- Multiple import paths for same class
- Compatibility shims required

## Test Discovery

### Existing Tests Analysis (300+ test files found)
**Mission Critical Tests (Must Pass):**
- `test_websocket_agent_events_suite.py` - 5 critical WebSocket events
- `test_websocket_ssot_violations_issue_885.py` - Currently failing (should pass after fix)
- `test_unified_manager.py` - Core implementation tests

**Key Test Categories:**
- Unit Tests: 80+ files for SSOT compliance
- Integration Tests: 50+ files for cross-service validation
- Performance Tests: Ensure no degradation

### Test Plan Summary

**Phase 1 - Pre-Consolidation Baseline:**
```bash
python tests/unit/websocket_ssot/test_websocket_manager_ssot_consolidation.py
python tests/mission_critical/test_websocket_agent_events_suite.py
python netra_backend/tests/unit/websocket_core/test_unified_manager.py
```

**Phase 2 - During Consolidation:**
- Import compatibility tests must continue working
- Factory pattern validation
- User isolation tests

**Phase 3 - Post-Consolidation:**
- SSOT violation tests should now pass
- Single manager validation
- Performance regression tests

### New Tests Needed
1. **Consolidation Validation Test** - Verify only one manager exists
2. **Migration Safety Test** - Ensure connections preserved
3. **Performance Impact Test** - Validate no throughput degradation

## Remediation Plan

### Decision: Consolidate to `unified_manager.py` as SSOT

**Why unified_manager.py:**
- Contains actual implementation (`_UnifiedWebSocketManagerImplementation`)
- websocket_manager.py is mostly factory functions
- manager.py already configured as compatibility layer

### Atomic Migration Strategy

**Phase 1: Core Consolidation (Immediate)**
1. Move factory logic from websocket_manager.py to unified_manager.py
2. Convert websocket_manager.py to re-export facade
3. Maintain all import paths for backward compatibility
4. Single atomic commit for safety

**Phase 2: Import Updates (1 week)**
1. Update production code to use canonical imports
2. Add deprecation warnings to legacy paths
3. Update test imports incrementally

**Phase 3: Cleanup (Optional, 1 month)**
1. Remove manager.py compatibility layer
2. Remove facade after all imports updated
3. Final SSOT validation

### Success Criteria
- ✅ All 5 WebSocket events continue working
- ✅ All 1,700+ imports remain functional
- ✅ User isolation patterns preserved
- ✅ New SSOT tests pass
- ✅ No performance degradation

### Risk Mitigation
- **High Risk:** Golden Path - Test all WebSocket events before/after
- **Medium Risk:** Import breaks - Phased migration with compatibility
- **Low Risk:** Test updates - Incremental changes

## Test Execution Results

### New Test Created
- `/tests/unit/websocket_ssot/test_manager_consolidation_validation.py` ✅
  - Tests verify single manager implementation
  - Tests check import path consistency  
  - Tests validate legacy feature support

### Baseline Test Results
- `test_websocket_agent_events_suite.py` - PASSED (5 critical events working)
- `test_unified_manager.py` - PASSED (core implementation stable)
- New consolidation validation test - FAILING (correctly detects violations)

### Current SSOT Violation Status
- **3 manager implementations detected** (expecting 1)
- **Import paths inconsistent** (multiple paths for same functionality)
- **Legacy features scattered** across implementations

## Progress Log
- 2025-09-17: Initial SSOT audit complete
- 2025-09-17: Critical violations identified
- 2025-09-17: Test plan created and executed
- 2025-09-17: New SSOT validation tests working correctly