# SSOT Gardener Work Tracker: RequestScopedToolDispatcher Multiple Competing Implementations

**Issue:** https://github.com/netra-systems/netra-apex/issues/234  
**Priority:** P0 CRITICAL - $500K+ ARR at risk  
**Status:** 🔄 IN PROGRESS  

## Executive Summary

Multiple competing tool dispatcher implementations violating SSOT principles and breaking WebSocket event delivery for chat functionality (90% of platform value).

## Critical SSOT Violations Identified

### P0 CRITICAL
1. **Multiple Dispatcher Implementations**
   - `netra_backend/app/agents/request_scoped_tool_dispatcher.py:58` (566 lines)
   - `netra_backend/app/core/tools/unified_tool_dispatcher.py:95` (1,084+ lines)  
   - `netra_backend/app/agents/tool_dispatcher_core.py:38` (LEGACY)

2. **Factory Pattern Chaos** - 4+ competing implementations
   - `ToolExecutorFactory`
   - `UnifiedToolDispatcherFactory` 
   - `ToolDispatcher.create_request_scoped_dispatcher()`
   - `create_request_scoped_tool_dispatcher()` functions

3. **WebSocket Bridge Adapter Duplication**
   - RequestScopedToolDispatcher has own WebSocketBridgeAdapter
   - Competing with existing AgentWebSocketBridge patterns

### P1 HIGH  
4. **Legacy Import Bypass** - 32+ files bypassing SSOT patterns
5. **Incomplete SSOT Migration** - Dangerous hybrid state

## Golden Path Impact
**BLOCKING:** Users login → WebSocket race conditions → Agent execution inconsistency → AI response failures

## Process Tracking

### ✅ COMPLETED
- [x] SSOT Audit Discovery (Step 0)
- [x] GitHub Issue Created (#234)
- [x] IND File Created

### 🔄 CURRENT
- [ ] Test Discovery and Planning (Step 1)

### ⏳ PENDING  
- [ ] Execute Test Plan (Step 2)
- [ ] Plan SSOT Remediation (Step 3)
- [ ] Execute Remediation (Step 4)
- [ ] Test Fix Loop (Step 5)
- [ ] PR Creation and Closure (Step 6)

## Test Strategy (PLANNED)

### Existing Tests to Validate
- Mission critical WebSocket event suite
- Agent execution integration tests
- Tool dispatcher unit tests

### New Tests Needed (~20%)
- SSOT compliance validation for dispatcher factories
- WebSocket event delivery consistency tests
- User isolation verification across factory patterns

### Test Categories
- Unit tests (no docker)
- Integration tests (no docker) 
- E2E tests on staging GCP

## Remediation Strategy (PLANNED)

### Phase 1: Factory Consolidation (CRITICAL)
- Consolidate all factory patterns into UnifiedToolDispatcherFactory
- Ensure consistent WebSocket-enabled instances

### Phase 2: Implementation Merge (HIGH)
- Merge RequestScopedToolDispatcher into UnifiedToolDispatcher
- Maintain API compatibility

### Phase 3: WebSocket Bridge SSOT (HIGH)  
- Consolidate WebSocketBridgeAdapter implementations
- Ensure 5 critical events delivered consistently

### Phase 4: Import Migration Cleanup (MEDIUM)
- Complete test file migration to SSOT imports
- Remove legacy patterns

## Risk Assessment
- **HIGH RISK** but necessary for Golden Path stability
- **75% migration complete** - dangerous hybrid state
- **Timeline:** 1-2 development cycles critical

---
*Last Updated: 2025-09-10*  
*Next: Test Discovery and Planning*