# SSOT-regression-duplicate-UserMessageHandler-blocking-golden-path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1099  
**Priority:** P0 - Critical Golden Path Blocker  
**Business Impact:** $500K+ ARR - Complete golden path flow blocked

## SSOT Violation Discovered

### Problem Summary
Two competing UserMessageHandler implementations creating message routing conflicts:

1. **Legacy Implementation:** `/netra_backend/app/services/websocket/message_handler.py:160`
   - Uses deprecated queue-based pattern
   - Requires `supervisor, db_session_factory` parameters
   - Bypasses SSOT AgentInstanceFactory

2. **SSOT Implementation:** `/netra_backend/app/websocket_core/handlers.py:1197` 
   - Modern SSOT-compliant pattern
   - Parameter-less initialization
   - Proper agent factory integration

### Golden Path Impact
- **Message Routing Failures:** Import confusion between two implementations
- **Agent Execution Breakdown:** Legacy patterns conflict with SSOT agent execution
- **WebSocket Event Failures:** Race conditions prevent proper event delivery
- **User Isolation Compromised:** Legacy bypasses proper factory patterns

## Remediation Plan

### Phase 1: Test Discovery and Planning
- [ ] Discover existing tests protecting message handling
- [ ] Plan new SSOT validation tests
- [ ] Create failing tests demonstrating SSOT violation

### Phase 2: SSOT Remediation Execution  
- [ ] DELETE legacy `/netra_backend/app/services/websocket/message_handler.py`
- [ ] UPDATE all imports to SSOT websocket_core handlers
- [ ] VALIDATE AgentMessageHandler routing through SSOT patterns
- [ ] ENSURE proper user isolation through factory patterns

### Phase 3: Validation and Stability
- [ ] Run all existing tests (must pass or be updated)
- [ ] Execute new SSOT validation tests
- [ ] Verify golden path user flow works end-to-end
- [ ] Validate WebSocket event delivery

## Progress Log

### 2025-09-14 - Discovery Complete
- ✅ Critical SSOT violation identified and documented
- ✅ GitHub issue #1099 created
- ✅ Local progress tracking file established
- 🔄 NEXT: Discover existing tests and plan test coverage

## Test Status
- **Existing Tests:** Discovery pending
- **New SSOT Tests:** Planning pending  
- **Validation Status:** Not started

## Files Involved
- `/netra_backend/app/services/websocket/message_handler.py` (DELETE)
- `/netra_backend/app/websocket_core/handlers.py` (SSOT)
- All files importing UserMessageHandler (UPDATE)

## Business Validation
- **Segment:** Platform-wide
- **Goal:** Enable golden path functionality
- **Impact:** Restore core agent execution and message routing
- **Revenue Impact:** Unblock $500K+ ARR chat functionality