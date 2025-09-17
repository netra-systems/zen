# WebSocket Bridge Configuration Crisis - P0 Critical Issue

## 🚨 Priority: P0 - BLOCKING GOLDEN PATH

**Error Location:** `/netra_backend/app/smd.py` line 590
**Error:** `'AgentWebSocketBridge' object has no attribute 'configure'`
**Impact:** Factory initialization failure preventing service startup

## Problem Statement

The service startup is failing during Phase 5 (Factory Pattern Initialization) due to a missing or incorrect `configure` method call on the `AgentWebSocketBridge` object. This is preventing the Golden Path user flow from functioning.

## Root Cause Analysis

1. **Factory Initialization in smd.py line 2175:**
   ```python
   websocket_factory.configure(
       connection_pool=connection_pool,
       agent_registry=None,  # Per-request in UserExecutionContext pattern
       health_monitor=health_monitor
   )
   ```

2. **Expected Object:** Code expects `AgentWebSocketBridge` with `configure` method
3. **Actual Object:** The object being returned may not be the expected type or may be missing the method
4. **SSOT Compliance:** This affects the Single Source of Truth pattern for WebSocket bridge management

## Evidence

- Line 2162-2163 in smd.py: `websocket_factory = create_agent_websocket_bridge()`
- Line 2175: `websocket_factory.configure(...)` call fails
- The `AgentWebSocketBridge` class DOES have a `configure` method (confirmed in `/netra_backend/app/services/agent_websocket_bridge.py` line 189)

## Impact Assessment

- **Business Impact:** HIGH - Blocks 90% of platform value (chat functionality)
- **Golden Path:** BLOCKED - Users cannot login → get AI responses
- **Revenue Risk:** $500K+ ARR at risk due to core functionality failure
- **Development Velocity:** CRITICAL - All development blocked until resolved

## Investigation Required

1. Verify the return type of `create_agent_websocket_bridge()`
2. Check if the wrong factory method is being called
3. Validate that the object being configured is actually an `AgentWebSocketBridge` instance
4. Review recent changes to factory pattern implementation

## Temporary Workaround

Consider implementing defensive programming:
```python
if hasattr(websocket_factory, 'configure'):
    websocket_factory.configure(...)
else:
    logger.critical(f"WebSocket factory missing configure method: {type(websocket_factory)}")
```

## Required for Resolution

- [ ] Identify why `create_agent_websocket_bridge()` doesn't return expected type
- [ ] Fix factory method to return proper `AgentWebSocketBridge` instance
- [ ] Validate SSOT compliance for WebSocket bridge factory pattern
- [ ] Test Golden Path user flow after fix
- [ ] Update factory pattern documentation if needed

## Context

This issue is part of the broader WebSocket Bridge Configuration Crisis identified during the test infrastructure audit on 2025-09-17. The Golden Path user flow (login → AI responses) depends on proper WebSocket bridge initialization for real-time agent communication.