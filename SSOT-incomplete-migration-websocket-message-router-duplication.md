# SSOT-incomplete-migration-websocket-message-router-duplication

## Critical SSOT Violation: Multiple WebSocket Message Router Implementations

### Status
- **Priority:** P0 CRITICAL
- **Impact:** Blocks golden path - users cannot reliably get AI responses
- **Business Impact:** $500K+ ARR at risk - affects 90% of platform value (chat)

### Violation Details
Multiple competing WebSocket message router implementations exist:

1. **Duplicate CanonicalMessageRouter Classes:**
   - `/netra_backend/app/websocket_core/canonical_message_router.py` (Line 94)
   - `/netra_backend/app/websocket_core/handlers.py` (Line 1351)

2. **Circular/Duplicate Router Inheritance:**
   - `MessageRouter(ExternalCanonicalMessageRouter)` in handlers.py creates circular dependencies

3. **Inconsistent WebSocket Manager Import Patterns:**
   - Two different import paths for `get_websocket_manager` in example_message_processor.py

### Why This Blocks Golden Path
- Messages may be processed by wrong router
- WebSocket events (agent_started, etc.) delivered inconsistently
- Agent responses may not reach correct users
- Factory pattern user isolation can break

### Test Plan
- [ ] Find existing WebSocket message routing tests
- [ ] Create test to validate single router implementation
- [ ] Test WebSocket event delivery through correct router
- [ ] Test user isolation in message routing

### Remediation Plan
- [ ] Consolidate to single CanonicalMessageRouter in canonical_message_router.py
- [ ] Remove duplicate in handlers.py
- [ ] Update all imports to use SSOT WebSocket manager factory
- [ ] Ensure all 5 critical WebSocket events flow correctly

### Progress Log
- 2025-09-17: Issue discovered and documented