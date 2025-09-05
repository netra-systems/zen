# WebSocket Event Pipeline Failure - Root Cause Analysis
**Date:** 2025-01-02
**Severity:** CRITICAL 
**Business Impact:** $500K+ ARR at risk - Core chat functionality broken in staging

## Executive Summary
WebSocket agent events test suite shows NO required events being transmitted in staging environment. Only receiving 'ack' events instead of critical agent lifecycle events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed). This is a complete failure of the core chat functionality value delivery mechanism.

## Five Whys Root Cause Analysis

### Why #1: Why aren't WebSocket events being transmitted?
**FINDING:** The system is using the **DEPRECATED WebSocketNotifier** instead of the current AgentWebSocketBridge.

**Evidence:**
- Line 4 in `netra_backend/app/agents/supervisor/websocket_notifier.py`: 
  ```python
  ⚠️  DEPRECATION WARNING ⚠️ 
  This module is DEPRECATED. Use AgentWebSocketBridge instead.
  ```
- Line 47: Another deprecation warning indicating AgentWebSocketBridge should be used
- Test suite imports deprecated components from `WebSocketNotifier` path

### Why #2: Why is the system still using deprecated WebSocketNotifier?
**FINDING:** The migration from WebSocketNotifier to AgentWebSocketBridge was **INCOMPLETE**. 

**Evidence:**
- `netra_backend/app/agents/supervisor/agent_registry.py` Line 72: `set_websocket_manager()` calls `create_agent_websocket_bridge()` - this is correct
- But the actual execution engines and agent implementations still reference the old WebSocketNotifier patterns
- Line 39 in `execution_engine.py`: "WebSocketNotifier deprecated - using AgentWebSocketBridge instead" (comment only, not implemented)

### Why #3: Why was the migration incomplete?
**FINDING:** The **FACTORY PATTERN MIGRATION** was implemented but not properly wired to the execution flow.

**Evidence:**
- `netra_backend/app/services/agent_websocket_bridge.py` Line 2377: Factory function `create_agent_websocket_bridge()` exists
- Line 93-96 in `agent_registry.py`: Bridge is created but not properly connected to agent execution pipeline
- The ExecutionEngine at Line 100 **throws RuntimeError** for direct instantiation, forcing factory usage, but the WebSocket event emission isn't wired through the new factory-created bridges

### Why #4: Why isn't the factory pattern properly wired?
**FINDING:** **SINGLETON PATTERN CONFLICTS** with user isolation requirements cause initialization failures.

**Evidence:**
- Line 67 in `execution_engine.py`: "ExecutionEngine" class documentation warns about global state being unsafe for concurrent users
- Line 100: RuntimeError thrown on direct instantiation to prevent singleton usage  
- The system tries to use request-scoped execution but the WebSocket event emission paths still expect singleton WebSocket managers
- Factory pattern exists but the **actual agent execution code paths don't use the factory-created emitters**

### Why #5: Why don't agent execution paths use factory-created emitters?
**FINDING:** **ARCHITECTURAL INCONSISTENCY** - The refactoring removed singleton patterns but didn't update all the event emission callsites.

**Evidence:**
- Agents still try to use global WebSocket managers instead of request-scoped emitters
- Line 212-213 in `supervisor_consolidated.py`: Tries to call `set_websocket_manager()` on tool_dispatcher which may not exist
- The `dependencies.py` Line 347-349: WebSocket manager is set on agent_registry but doesn't propagate to actual agent instances during execution
- **The "error behind the error"**: The test shows only 'ack' events because the WebSocket connection is established, but no agent lifecycle events are being emitted through the proper channels

## Root Cause Summary
**PRIMARY ROOT CAUSE:** Incomplete migration from deprecated WebSocketNotifier to AgentWebSocketBridge factory pattern. The WebSocket infrastructure was refactored to use factories for user isolation, but the agent execution pipeline still references the old singleton-based event emission paths that no longer function.

**SECONDARY ROOT CAUSES:**
1. Agent execution engines aren't using factory-created WebSocket emitters
2. WebSocket event emission is not properly wired through the new AgentWebSocketBridge
3. Test environment may be using different WebSocket initialization paths than production code

## Critical Code Locations Requiring Fixes

### 1. Agent Execution Context (`netra_backend/app/agents/supervisor/execution_engine.py`)
- **Line 88-100**: ExecutionEngine constructor blocks direct instantiation
- **Issue**: No alternative initialization path for WebSocket event emission
- **Fix**: Implement factory-based WebSocket emitter initialization in request-scoped engines

### 2. Agent Registry WebSocket Integration (`netra_backend/app/agents/supervisor/agent_registry.py`)
- **Line 93-96**: Bridge is created but not propagated to agent execution
- **Issue**: Factory-created bridge isn't passed to actual agent instances  
- **Fix**: Ensure `create_agent_websocket_bridge()` result is used by agent execution contexts

### 3. Dependencies WebSocket Setup (`netra_backend/app/dependencies.py`)
- **Line 347-349**: WebSocket manager set on registry but not propagated to agents
- **Issue**: Bridge creation doesn't flow through to agent instances during execution
- **Fix**: Verify WebSocket manager propagation through entire execution pipeline

### 4. Agent Execution Pipeline Emission Points
- Multiple agent files like `unified_data_agent.py`, `actions_to_meet_goals_sub_agent.py` 
- **Issue**: Using old event emission patterns that don't connect to new factory-created bridges
- **Fix**: Update all `emit_agent_started()` and similar calls to use factory-created emitters

## Specific Configuration Issues in Staging

### Missing WebSocket Manager Initialization
The factory pattern requires proper initialization sequence:
1. WebSocket manager must be created first
2. AgentWebSocketBridge factory must be called with user context  
3. Bridge must be properly connected to agent execution contexts
4. Agent instances must use bridge-provided emitters, not global references

### Test Environment vs Production Discrepancy  
Test suite may be using different initialization paths than the actual staging deployment, masking the real issue.

## Immediate Action Required

### Phase 1: Restore Event Emission (Critical - 0-2 hours)
1. **Identify the actual event emission callsites** in agent execution
2. **Trace why factory-created bridges aren't being used** for event emission
3. **Fix the connection between AgentWebSocketBridge factory and agent instances**

### Phase 2: Verify End-to-End Flow (Critical - 2-4 hours) 
1. **Test that `create_agent_websocket_bridge()` result is used** by execution engines
2. **Validate WebSocket events flow** through factory-created emitters
3. **Run mission critical test suite** to verify all 5 required events are transmitted

### Phase 3: Staging Environment Validation (High - 4-6 hours)
1. **Deploy fixed version to staging**
2. **Run live WebSocket event validation** in staging environment  
3. **Verify no regression in user isolation** while enabling event transmission

## Next Steps
The fix requires completing the WebSocket factory pattern migration by ensuring that:
1. All agent execution paths use factory-created WebSocket emitters
2. The AgentWebSocketBridge factory results are properly wired to agent instances
3. Event emission flows through the new architecture instead of deprecated paths

This is a **CRITICAL deployment blocker** that must be resolved before any staging or production deployments.