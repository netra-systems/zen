# SSOT-incomplete-migration-websocket-manager-import-path-fragmentation-blocks-golden-path

**GitHub Issue:** [#1104](https://github.com/netra-systems/netra-apex/issues/1104)
**Created:** 2025-09-14
**Priority:** HIGH - Blocks Golden Path WebSocket events
**Status:** 🔧 PARTIAL IMPLEMENTATION

## Problem Summary
Multiple conflicting import paths for WebSocketManager creating initialization race conditions and inconsistent WebSocket event delivery critical for Golden Path user flow.

## Files Affected
- `/netra_backend/app/dependencies.py`
- `/netra_backend/app/services/agent_websocket_bridge.py`
- `/netra_backend/app/factories/websocket_bridge_factory.py`
- `/netra_backend/app/agents/supervisor/agent_instance_factory.py`

## Conflicting Import Patterns Found
```python
# PATTERN 1:
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# PATTERN 2:
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
```

## Business Impact
- **Revenue Risk:** $500K+ ARR depends on reliable WebSocket events
- **User Experience:** Inconsistent real-time chat functionality
- **Golden Path Blocker:** Race conditions prevent agent event delivery

## SSOT Compliance Goal
Consolidate to single canonical WebSocket manager import path following SSOT principles.

---

## Process Progress

### ✅ Step 0: DISCOVER Next SSOT Issue (COMPLETE)
- [x] SSOT audit complete - identified WebSocket manager fragmentation
- [x] GitHub issue #1104 created
- [x] Progress tracker (this file) created
- [x] Next: Move to Step 1 - Test Discovery and Planning

### ✅ Step 1: DISCOVER AND PLAN TEST (COMPLETE)
- [x] 1.1 DISCOVER EXISTING: Found 100+ WebSocket tests across mission critical, integration, and unit test categories
- [x] 1.2 PLAN ONLY: Designed comprehensive test strategy (20% new SSOT tests, 60% existing validation, 20% consolidation tests)
- [x] Confirmed import fragmentation: 3 files use legacy paths, 1 uses SSOT unified_manager
- [x] Test execution strategy: No Docker required (unit/integration/staging E2E)
- [x] Business value protection: All tests safeguard $500K+ ARR WebSocket functionality

### ✅ Step 2: EXECUTE THE TEST PLAN (COMPLETE)
- [x] Created 3 NEW SSOT validation test files (20% new tests)
- [x] All tests FAIL as expected - proving Issue #1104 exists
- [x] Detected 4 legacy import violations across 3 files
- [x] Tests ready for post-fix validation (currently failing by design)
- [x] No Docker dependencies - unit/integration/staging compatible
### ✅ Step 3: PLAN REMEDIATION OF SSOT (COMPLETE)
- [x] Design import path consolidation strategy (comprehensive plan created)
- [x] Plan migration sequence to minimize disruption (3-phase plan)
- [x] Identify backward compatibility requirements (alias preservation) 
### 🔧 Step 4: EXECUTE THE REMEDIATION SSOT PLAN (PARTIAL - 1/3 COMPLETE)
- [x] ✅ Phase 2: Agent Instance Factory COMPLETE (already fixed)
- [ ] 🔄 Phase 1: Dependencies.py (NEXT - legacy import on line 16)
- [ ] ⏳ Phase 3: Agent WebSocket Bridge (legacy imports on lines 25, 3318)
### ⏳ Step 5: ENTER TEST FIX LOOP (PENDING)
### ⏳ Step 6: PR AND CLOSURE (PENDING)

## Test Discovery Findings

### Existing Test Coverage (100+ tests found)
- **Mission Critical Tests:** `tests/mission_critical/test_websocket_*` - 80+ tests protecting $500K+ ARR
- **Integration Tests:** WebSocket bridge, factory patterns - 50+ tests
- **Unit Tests:** Manager classes, connections - 70+ tests

### Import Path Fragmentation Confirmed
- **Legacy Path (3 files):** `from netra_backend.app.websocket_core.websocket_manager import WebSocketManager`
  - `dependencies.py` ❌
  - `agent_websocket_bridge.py` ❌
  - `agent_instance_factory.py` ❌
- **SSOT Path (1 file):** `from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager`
  - `websocket_bridge_factory.py` ✅

## SSOT Test Results (Step 2)

### Created Test Files
- **`tests/unit/ssot/test_websocket_manager_import_path_violations.py`** - Import violation detection
- **`tests/unit/ssot/test_websocket_manager_ssot_compliance.py`** - SSOT compliance validation  
- **`tests/integration/websocket/test_websocket_manager_initialization_race.py`** - Race condition testing

### Current Violations Status (3 legacy imports across 2 files)
- **`/netra_backend/app/dependencies.py`** (Line 16) ❌ PENDING
- **`/netra_backend/app/services/agent_websocket_bridge.py`** (Lines 25, 3318) ❌❌ PENDING
- **`/netra_backend/app/agents/supervisor/agent_instance_factory.py`** ✅ **FIXED** (SSOT compliant)

### Test Results
- **All tests FAIL as expected** ✅ - proving Issue #1104 exists  
- **4 specific violations found** ✅ - exact locations identified
- **Race conditions confirmed** ✅ - concurrent initialization issues detected

### SSOT Consolidation Strategy
- **Target:** Consolidate all imports to unified_manager (SSOT)
- **Method:** Update 3 legacy files to use canonical import path
- **Validation:** 20% new tests + 60% existing test compatibility + 20% success validation

---

## Notes
- Focus on Golden Path: users login → get AI responses
- WebSocket events critical for 90% of platform value
- Import path consolidation must maintain existing functionality
- All changes must pass existing tests + new SSOT validation tests