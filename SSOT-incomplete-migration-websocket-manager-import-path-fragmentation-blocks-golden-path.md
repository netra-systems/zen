# SSOT-incomplete-migration-websocket-manager-import-path-fragmentation-blocks-golden-path

**GitHub Issue:** [#1104](https://github.com/netra-systems/netra-apex/issues/1104)
**Created:** 2025-09-14
**Priority:** HIGH - Blocks Golden Path WebSocket events
**Status:** 🔍 DISCOVERY COMPLETE

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

### 🔄 Step 1: DISCOVER AND PLAN TEST (PENDING)
- [ ] 1.1 DISCOVER EXISTING: Find tests protecting WebSocket manager functionality
- [ ] 1.2 PLAN ONLY: Design test strategy for SSOT remediation validation

### ⏳ Step 2: EXECUTE THE TEST PLAN (PENDING)
### ⏳ Step 3: PLAN REMEDIATION OF SSOT (PENDING) 
### ⏳ Step 4: EXECUTE THE REMEDIATION SSOT PLAN (PENDING)
### ⏳ Step 5: ENTER TEST FIX LOOP (PENDING)
### ⏳ Step 6: PR AND CLOSURE (PENDING)

---

## Notes
- Focus on Golden Path: users login → get AI responses
- WebSocket events critical for 90% of platform value
- Import path consolidation must maintain existing functionality
- All changes must pass existing tests + new SSOT validation tests