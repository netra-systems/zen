# WebSocket Bridge Unification Plan

## Executive Summary
Critical SSOT violation: Three different WebSocket communication patterns exist across agent files, causing confusion and maintenance issues. This plan provides a comprehensive solution to unify all WebSocket communication through a single bridge pattern.

## Current State Analysis

### Pattern Distribution
- **Pattern 1 (Bridge)**: ~15-20 files using WebSocketBridgeAdapter
- **Pattern 2 (Manager)**: ~10-15 files using WebSocket manager directly  
- **Pattern 3 (Mixed)**: ~20-25 files with inconsistent usage

### Critical Issues Identified

#### 1. Duplicate Method Implementations
- `send_agent_thinking()` exists in 3+ locations
- `send_partial_result()` exists in 3+ locations
- `send_tool_executing()` exists in 3+ locations
- `send_final_report()` exists in 3+ locations

#### 2. Inconsistent Event Routing
- Some files check `websocket_manager` but use bridge
- Some files use bridge directly
- Some files have both patterns mixed

#### 3. Constructor Pollution
- Nearly every agent takes `websocket_manager` parameter
- Most don't actually use it directly
- Creates confusion about which pattern is active

## Proposed Solution: Unified WebSocket Bridge Pattern

### Architecture Overview
```
┌─────────────────┐
│   Agent/Mixin   │
├─────────────────┤
│ emit_thinking() │
│ emit_tool_*()   │
│ emit_progress() │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ WebSocketBridgeAdapter  │ (SSOT)
├─────────────────────────┤
│ - Unified interface     │
│ - Bridge management     │
│ - Event standardization │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ AgentWebSocketBridge    │ (Singleton)
├─────────────────────────┤
│ - Event routing         │
│ - Manager integration   │
│ - Error handling        │
└─────────────────────────┘
```

### Implementation Strategy

#### Phase 1: Standardize Bridge Pattern (IMMEDIATE)
1. **BaseSubAgent Enhancement**
   - Already has WebSocketBridgeAdapter integrated
   - Provides emit_* methods for all events
   - Remove websocket_manager parameter

2. **Remove Direct Manager Usage**
   - Replace all `self.websocket_manager.send_*` calls
   - Use `emit_*` methods from bridge adapter
   - Remove manager references from constructors

3. **Clean Up Mixed Usage**
   - Remove duplicate WebSocket methods
   - Consolidate to single emission path
   - Delete legacy compatibility code

#### Phase 2: Migration Path

##### Files to Migrate (Priority Order)

**Critical - Mixed Usage (Fix First)**
1. `agent_communication.py` - Remove direct bridge calls, use adapter
2. `agent_lifecycle.py` - Remove manager checks, use adapter
3. `base/interface.py` - Remove duplicate methods, route through adapter

**High - Direct Manager Usage**
4. `chat_orchestrator/trace_logger.py` - Replace manager with bridge
5. `supervisor/workflow_orchestrator.py` - Use bridge pattern
6. `supervisor/pipeline_executor.py` - Migrate to bridge

**Medium - Legacy Patterns**
7. Remove `websocket_manager` parameter from all constructors
8. Delete deprecated WebSocketContextMixin references
9. Clean up "no longer needed" dead code

### Code Changes Required

#### Example Migration: agent_communication.py
```python
# BEFORE (Mixed Pattern)
async def _attempt_websocket_update(self, run_id: str, data: Dict) -> None:
    bridge = await get_agent_websocket_bridge()
    if status == "thinking":
        await bridge.notify_agent_thinking(run_id, self.name, message)
    # ... more bridge calls

# AFTER (Unified Pattern) 
async def _attempt_websocket_update(self, run_id: str, data: Dict) -> None:
    if status == "thinking":
        await self.emit_thinking(message)
    # ... use emit_* methods
```

#### Example Migration: Remove Manager from Constructor
```python
# BEFORE
def __init__(self, websocket_manager=None, ...):
    self.websocket_manager = websocket_manager

# AFTER
def __init__(self, ...):
    # WebSocket handled via bridge adapter
    pass
```

### Testing Strategy

#### Unit Tests
- Test each emit_* method works correctly
- Verify bridge singleton behavior
- Check error handling paths

#### Integration Tests
- Test agent lifecycle with bridge
- Verify event flow end-to-end
- Test concurrent agent emissions

#### E2E Tests
- Validate WebSocket events reach frontend
- Test real agent execution flows
- Verify no duplicate events

### Success Metrics
- **SSOT Compliance**: 100% (from current ~30%)
- **Code Duplication**: 0 duplicate WebSocket methods
- **Constructor Cleanup**: 0 websocket_manager parameters
- **Test Coverage**: 95%+ for WebSocket paths

### Risk Mitigation
1. **Backward Compatibility**: Keep emit_* methods that map to new pattern
2. **Gradual Migration**: File-by-file approach with tests
3. **Monitoring**: Add logging to track migration progress
4. **Rollback Plan**: Git branches for each migration phase

### Timeline
- **Day 1**: Fix critical mixed-usage files (3-4 hours)
- **Day 2**: Migrate manager-dependent files (4-5 hours)
- **Day 3**: Clean up and test thoroughly (3-4 hours)
- **Total**: 10-13 hours of focused work

## Implementation Checklist

### Immediate Actions
- [ ] Fix agent_communication.py mixed patterns
- [ ] Fix agent_lifecycle.py mixed patterns  
- [ ] Fix base/interface.py duplicate methods
- [ ] Create migration test suite

### Short Term (This Week)
- [ ] Remove websocket_manager from all constructors
- [ ] Migrate all manager-dependent files
- [ ] Delete dead WebSocket code
- [ ] Update all imports and references

### Validation
- [ ] Run WebSocket consistency tests
- [ ] Verify E2E WebSocket flow
- [ ] Check no duplicate events
- [ ] Confirm SSOT compliance

## Conclusion
The unified WebSocket bridge pattern will eliminate the current chaos of three different patterns, reduce code by ~30%, and make the system maintainable. The migration is straightforward and can be completed in 2-3 days with proper testing.