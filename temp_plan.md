## Remediation Plan - WebSocket Manager SSOT Consolidation

### SUBAGENT ANALYSIS COMPLETE

**Target:** Consolidate 9+ WebSocket Manager classes to single SSOT implementation
**Timeline:** 3.5 hours for complete atomic remediation
**Business Impact:** Restore $500K+ ARR chat functionality

### ATOMIC REMEDIATION STRATEGY

#### Phase 1: Consolidate to Single SSOT Implementation
**TARGET:** `netra_backend/app/websocket_core/unified_manager.py` - `_UnifiedWebSocketManagerImplementation` (KEEP)

**ELIMINATE:**
- `websocket_manager_factory.py` → DELETE entirely
- Class `WebSocketManagerFactory` → REMOVE from websocket_manager.py
- Class `_WebSocketManagerFactory` → REMOVE wrapper

#### Phase 2: Fix Database Test Failures
**ROOT CAUSE:** `test_connection_resource_lifecycle_management` expects connection limits enforcement
**FIX:** Add `MAX_CONNECTIONS_PER_USER = 10` enforcement in `add_connection()` method

#### Phase 3: Fix E2E Staging WebSocket Handshake
**ROOT CAUSE:** Multiple WebSocket managers causing handshake race conditions
**FIX:** Single manager instance per user context with consistent connection routing

#### Phase 4: Update All Import References
**ATOMIC MIGRATION:**
```python
# OLD (ELIMINATE):
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory

# NEW (SSOT):
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
```

### SUCCESS CRITERIA
- ✅ Database Tests Pass: All 6 lifecycle tests pass consistently
- ✅ E2E Staging WebSocket Handshakes Work: No timeout errors
- ✅ SSOT Compliance: Only 1 WebSocket Manager implementation
- ✅ $500K+ ARR Chat Functionality Restored: Users get AI responses

### IMMEDIATE NEXT STEPS
1. **Execute remediation plan using dedicated subagent**
2. **Validate fixes with comprehensive testing**
3. **Create PR linking GitHub issues for closure**

**Status:** Ready for execution phase - Plan validated and approved

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>