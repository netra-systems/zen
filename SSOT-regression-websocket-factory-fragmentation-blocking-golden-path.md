# SSOT Regression: WebSocket Factory Fragmentation Blocking Golden Path

**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/1103
**Status**: 🔍 DISCOVERY PHASE
**Priority**: 🚨 CRITICAL
**Impact**: Blocking $500K+ ARR Golden Path functionality

## Problem Summary

**SSOT Violation**: Dual WebSocket management patterns in `AgentInstanceFactory` creating race conditions and inconsistent event delivery, blocking the critical user login → AI response flow.

**Root Cause**: 
- ❌ Legacy Pattern: Direct `WebSocketManager` imports (Line 46)
- ✅ SSOT Pattern: `AgentWebSocketBridge` delegation (Line 47)
- 🚫 Conflict: Both patterns used in same factory class

## Technical Details

### Primary Violation Location
**File**: `/netra_backend/app/agents/supervisor/agent_instance_factory.py`
- **Line 46**: `from netra_backend.app.websocket_core.websocket_manager import WebSocketManager`
- **Line 98**: `self._websocket_manager: Optional[WebSocketManager] = None`
- **Line 47**: `from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge`

### Business Impact
- **Revenue Risk**: $500K+ ARR threatened by unreliable chat functionality
- **User Experience**: WebSocket events delivered inconsistently
- **Golden Path**: Users login but AI responses fail
- **System Integrity**: Race conditions in multi-user scenarios
- **Security**: User isolation failures possible

## Process Progress

### ✅ COMPLETED
- [x] **Step 0**: SSOT Audit completed - Critical violation identified
- [x] **GitHub Issue**: Created issue #1103 
- [x] **IND Creation**: Progress tracker established
- [x] **Initial Commit**: Progress tracker committed to repo

### 🔄 IN PROGRESS  
- [ ] **Step 1**: Discover and Plan Test
  - [ ] 1.1: Discover existing tests protecting WebSocket factory patterns
  - [ ] 1.2: Plan test suite for SSOT WebSocket factory validation

### 📋 PENDING
- [ ] **Step 2**: Execute test plan for SSOT validation (20% new tests)
- [ ] **Step 3**: Plan SSOT remediation strategy  
- [ ] **Step 4**: Execute SSOT remediation
- [ ] **Step 5**: Test fix loop - prove stability maintained
- [ ] **Step 6**: PR and closure

## Test Strategy (Planned)

### Existing Tests to Validate
- Mission critical WebSocket tests
- Agent instance factory tests  
- Golden Path user flow tests
- WebSocket bridge integration tests

### New SSOT Tests Needed (~20%)
- WebSocket factory SSOT compliance validation
- Agent WebSocket bridge consistency tests
- Multi-user isolation with SSOT patterns
- Factory bypass prevention tests

### Test Execution Focus
- ✅ Unit tests (no Docker required)
- ✅ Integration tests (no Docker required)  
- ✅ E2E tests on GCP staging (remote)
- ❌ Docker-based tests (excluded per instructions)

## Success Criteria

### Business Success
- [ ] **Golden Path**: Users login → get AI responses reliably
- [ ] **Revenue Protection**: $500K+ ARR chat functionality stable
- [ ] **Real-time UX**: All 5 WebSocket events delivered consistently
- [ ] **User Security**: No cross-user context leakage

### Technical Success  
- [ ] **SSOT Compliance**: Single WebSocket management path only
- [ ] **Factory Pattern**: Unified AgentWebSocketBridge usage
- [ ] **Import Cleanup**: Remove direct WebSocketManager imports
- [ ] **Type Safety**: Consistent typing across factory methods
- [ ] **Test Coverage**: All existing tests pass + new SSOT validation

## Remediation Plan (Detailed)

### Phase 1: Import and Type Cleanup
1. **Remove Legacy Import**: Line 46 `WebSocketManager` import
2. **Update Type Annotations**: Change `Optional[WebSocketManager]` to `Optional[AgentWebSocketBridge]`
3. **Standardize Factory Methods**: Use only `create_agent_websocket_bridge()`

### Phase 2: Factory Method Consolidation
1. **Unified Pattern**: Single WebSocket access method
2. **Bridge Integration**: All WebSocket operations via AgentWebSocketBridge
3. **Error Handling**: Consistent error patterns for WebSocket failures

### Phase 3: Validation and Testing
1. **SSOT Compliance**: Verify single source pattern
2. **Integration Testing**: Golden Path end-to-end validation
3. **Performance Testing**: No degradation in WebSocket performance
4. **Security Testing**: User isolation maintained

## Notes and Observations

### Key Learnings
- WebSocket factory fragmentation is a systemic SSOT pattern violation
- Direct manager imports bypass SSOT delegation patterns
- Golden Path reliability directly depends on consistent WebSocket event delivery
- User isolation security depends on factory pattern compliance

### Risks and Mitigation
- **Risk**: Breaking existing WebSocket functionality during refactor
  - **Mitigation**: Comprehensive test coverage before changes
- **Risk**: Performance degradation from pattern changes
  - **Mitigation**: Benchmark WebSocket performance before/after
- **Risk**: Missed import dependencies
  - **Mitigation**: Systematic import analysis and validation

---
**Last Updated**: 2025-09-14 - Discovery Phase Complete
**Next Action**: Begin Step 1 - Discover and Plan Test