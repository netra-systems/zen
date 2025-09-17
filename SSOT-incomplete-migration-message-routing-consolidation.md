# SSOT-incomplete-migration-message-routing-consolidation

**Issue Name:** SSOT-incomplete-migration-message-routing-consolidation
**GitHub Link:** [To be created]
**Created:** 2025-09-17

## Summary

Multiple message router implementations violate SSOT principles. CanonicalMessageRouter is designated SSOT, but WebSocketEventRouter and UserScopedWebSocketEventRouter still exist as parallel implementations.

## Critical SSOT Violations

### 1. Message Router Implementations (3 parallel systems)
- **SSOT:** `/netra_backend/app/websocket_core/canonical_message_router.py` - CanonicalMessageRouter (646 lines)
- **Legacy:** `/netra_backend/app/services/websocket_event_router.py` - WebSocketEventRouter  
- **Legacy:** `/netra_backend/app/services/user_scoped_websocket_event_router.py` - UserScopedWebSocketEventRouter

### 2. Handler Fragmentation
- `/netra_backend/app/websocket_core/handlers.py` - 27K+ lines mega-class
- `/netra_backend/app/services/message_handlers.py` - Service handlers
- `/netra_backend/app/websocket_core/agent_handler.py` - Agent handlers

### 3. Factory Pattern Violations
- Multiple factory functions: `create_message_router()`, `get_websocket_router()`, `create_user_event_router()`
- Inconsistent user context handling

## Business Impact
- WebSocket infrastructure has 0% unit test coverage (90% of platform value at risk)
- Multi-user isolation conflicts could cause cross-user message routing
- Performance overhead from multiple routing layers

## Test Discovery

### Existing Tests to Validate
- [ ] Identify tests for CanonicalMessageRouter
- [ ] Find tests for WebSocketEventRouter
- [ ] Locate handler-related tests
- [ ] Check integration tests for message routing

## Test Plan
- [ ] Create failing test showing SSOT violation
- [ ] Create test for CanonicalMessageRouter as sole router
- [ ] Create migration validation test

## Remediation Plan
- [ ] Phase 1: Complete WebSocketEventRouter migration to CanonicalMessageRouter adapters
- [ ] Phase 2: Migrate UserScopedWebSocketEventRouter to use CanonicalMessageRouter
- [ ] Phase 3: Consolidate handler registration patterns
- [ ] Phase 4: Remove legacy compatibility layers
- [ ] Phase 5: Update all imports and tests

## Progress Log

### Step 0: Discovery and Issue Creation
- Analyzed codebase for message routing SSOT violations
- Found 3 parallel router implementations
- Identified handler fragmentation issue
- Created tracking document

### Step 1: Test Discovery (Next)