# SSOT-incomplete-migration-multiple-websocket-managers

**GitHub Issue:** #844 - https://github.com/netra-systems/netra-apex/issues/844
**Priority:** P0 (CRITICAL/BLOCKING)
**Status:** DISCOVERED - Step 0 Complete
**Date Created:** 2025-01-13

## CRITICAL SSOT VIOLATION SUMMARY

Multiple WebSocket manager implementations violating SSOT principle and blocking Golden Path user flow (login → AI responses).

## EVIDENCE DISCOVERED

### File Locations:
- **Primary SSOT**: `/netra_backend/app/websocket_core/websocket_manager.py`
- **Competing Implementation**: `/netra_backend/app/websocket_core/unified_manager.py`  
- **Violation Point**: `/netra_backend/app/websocket_core/manager.py` imports from BOTH

### Code Evidence:
```python
# VIOLATION in manager.py: imports from TWO different WebSocket managers
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
```

## BUSINESS IMPACT ASSESSMENT

- **GOLDEN PATH BLOCKED**: Race conditions prevent users from getting AI responses
- **$500K+ ARR AT RISK**: Chat functionality = 90% of platform value (per CLAUDE.md)
- **SYSTEM INSTABILITY**: Dual WebSocket systems create undefined message delivery behavior
- **TEST EVIDENCE**: 164+ test files show WebSocket manager confusion

## CRITICAL REQUIREMENTS

All 5 WebSocket events must work for Golden Path:
1. `agent_started` - User sees agent began
2. `agent_thinking` - Real-time reasoning  
3. `tool_executing` - Tool transparency
4. `tool_completed` - Tool results
5. `agent_completed` - Completion signal

## PLANNED REMEDIATION APPROACH

1. **Phase 1**: Consolidate to single WebSocket manager (likely `websocket_manager.py`)
2. **Phase 2**: Update all imports to use single source
3. **Phase 3**: Remove duplicate `unified_manager.py` implementation  
4. **Phase 4**: Verify all 5 critical WebSocket events work end-to-end

## PROCESS TRACKING

- [x] **Step 0**: SSOT Audit Complete - Issue Created
- [ ] **Step 1**: Discover and Plan Test
- [ ] **Step 2**: Execute Test Plan for new SSOT tests
- [ ] **Step 3**: Plan Remediation of SSOT  
- [ ] **Step 4**: Execute Remediation SSOT Plan
- [ ] **Step 5**: Enter Test Fix Loop
- [ ] **Step 6**: PR and Closure

## NOTES

This is the #1 most critical SSOT violation identified because:
- Directly blocks Golden Path core functionality
- Violates fundamental SSOT principle with dual managers
- Creates race conditions in mission-critical chat system
- Has widespread impact across 164+ test files
- Affects $500K+ ARR business value according to CLAUDE.md

**Next Action**: Proceed to Step 1 - Discover and Plan Test