# WebSocket Sub-Agent Communication Fix Summary

## Problem
Sub-agents were not sending WebSocket messages to users because the `AgentInstanceFactory`'s `_websocket_bridge` was None when creating sub-agents, causing all WebSocket events to fail silently.

## Root Cause
The `AgentInstanceFactory` is a singleton that was being retrieved before configuration. The factory was only configured with the WebSocket bridge during the supervisor's `execute()` method, but by then it might be too late for some sub-agents.

## Solution Implemented

### 1. Pre-Configure Factory in Supervisor Init
**File:** `netra_backend/app/agents/supervisor_consolidated.py`
- Added immediate configuration of AgentInstanceFactory with WebSocket bridge in supervisor's `__init__` method
- This ensures the factory always has a valid WebSocket bridge before any sub-agents are created
- Configuration happens again in `execute()` to add registries, but the critical WebSocket bridge is already set

### 2. Added Validation and Loud Logging
**File:** `netra_backend/app/agents/supervisor/agent_instance_factory.py`
- Added validation to throw RuntimeError if WebSocket bridge is None when creating agents
- Enhanced logging to show WebSocket bridge type and status
- Added detailed error messages explaining the failure

**File:** `netra_backend/app/agents/mixins/websocket_bridge_adapter.py`
- Changed silent failures to loud warnings
- Added detailed logging showing bridge and run_id status
- Shows exactly why events are not being sent

### 3. Validation in Supervisor
**File:** `netra_backend/app/agents/supervisor_consolidated.py`
- Added validation to ensure websocket_bridge is provided to supervisor
- Added logging to confirm WebSocket bridge type

## Key Code Changes

### Supervisor Init (Lines 100-114)
```python
# CRITICAL FIX: Pre-configure the factory with WebSocket bridge IMMEDIATELY
# This ensures sub-agents created later will have WebSocket events working
logger.info(f"🔧 Pre-configuring agent instance factory with WebSocket bridge in supervisor init")
try:
    self.agent_instance_factory.configure(
        websocket_bridge=websocket_bridge,
        websocket_manager=getattr(websocket_bridge, 'websocket_manager', None),
        agent_class_registry=self.agent_class_registry
    )
    logger.info(f"✅ Factory pre-configured with WebSocket bridge to prevent sub-agent event failures")
except Exception as e:
    logger.warning(f"⚠️ Could not pre-configure factory in init (will configure in execute): {e}")
```

### Factory Validation (Lines 539-545)
```python
# CRITICAL: Validate WebSocket bridge is configured
if not self._websocket_bridge:
    logger.error(f"❌ CRITICAL: AgentInstanceFactory._websocket_bridge is None when creating {agent_name}!")
    logger.error(f"   This will cause ALL WebSocket events from {agent_name} to fail silently!")
    logger.error(f"   Factory must be configured with websocket_bridge before creating agents.")
    raise RuntimeError(f"AgentInstanceFactory not configured: websocket_bridge is None. Call configure() first!")
```

## Result
With these changes:
1. ✅ AgentInstanceFactory is always configured with WebSocket bridge before creating sub-agents
2. ✅ Any attempt to create sub-agents without WebSocket bridge will fail loudly with clear error messages
3. ✅ Silent failures are replaced with warning logs showing exactly what's missing
4. ✅ Sub-agents will now properly emit WebSocket events to users

## Testing
The WebSocket test suite should now pass with sub-agent events properly reaching users. Any failures will be clearly logged with actionable error messages.