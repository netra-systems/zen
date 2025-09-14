# SSOT Issue: Message Router Consolidation - Golden Path Blocker

**Issue Type:** SSOT-incomplete-migration-message-router-consolidation-blocks-golden-path
**Priority:** HIGH 
**Golden Path Impact:** CRITICAL - Blocks core chat functionality (90% of platform value)

## Problem Summary

Multiple MessageRouter implementations exist causing race conditions and message routing failures that directly block the Golden Path user flow of "login → get AI responses back."

## SSOT Violation Details

### Current Fragmented State
**4 Different MessageRouter Implementations Found:**

1. **SSOT Target (Primary):** `/netra_backend/app/websocket_core/handlers.py:1219`
   - Contains comprehensive handler registration
   - Should be the single source of truth

2. **Legacy Duplicate:** `/netra_backend/app/core/message_router.py:55`
   - Incomplete implementation
   - Causes import conflicts

3. **Specialized Duplicate:** `/netra_backend/app/services/websocket/quality_message_router.py:36`
   - QualityMessageRouter variant
   - Should extend SSOT implementation instead

4. **Test/Development Router:** Multiple test implementations

### Race Condition Pattern
```python
# Different routers get imported first depending on initialization order:
# Path A: websocket_core.handlers.MessageRouter
# Path B: core.message_router.MessageRouter  
# Path C: websocket.quality_message_router.QualityMessageRouter
# Result: Handler registration conflicts, message loss
```

## Business Impact

- **Revenue Risk:** $500K+ ARR threatened by broken chat functionality
- **User Experience:** Messages don't reach correct handlers
- **WebSocket Events:** Event routing failures prevent AI response delivery
- **Enterprise Risk:** Multi-user message contamination possible

## Golden Path Failure Mode

1. User sends chat message
2. Multiple routers compete for message handling
3. Message gets routed to wrong/incomplete handler
4. AI agent never receives message or responds to wrong user
5. User sees no AI response → Golden Path fails

## SSOT Compliance Plan

### Phase 1: Consolidate to Single Router
- Migrate all functionality to `websocket_core.handlers.MessageRouter`
- Remove duplicate implementations
- Update all imports to use SSOT router

### Phase 2: Extend Pattern for Quality Router
- Make QualityMessageRouter extend SSOT router
- Maintain specialized functionality without duplication

### Phase 3: Test Coverage
- Ensure comprehensive test coverage for consolidated router
- Validate no regression in message routing

## Files Requiring Update
- [ ] Remove: `/netra_backend/app/core/message_router.py`
- [ ] Update: `/netra_backend/app/services/websocket/quality_message_router.py`
- [ ] Update imports across codebase
- [ ] Update tests

## Success Criteria
- [ ] Single MessageRouter implementation (SSOT)
- [ ] All messages route correctly
- [ ] No handler registration conflicts
- [ ] Golden Path: User messages → AI responses work 100%
- [ ] All existing tests pass

## Next Steps
1. Audit all MessageRouter usage
2. Plan migration strategy
3. Execute consolidation
4. Validate Golden Path functionality

---
**Status:** In Progress - Step 0 Complete
**GitHub Issue:** TBD
**Updated:** 2025-09-14