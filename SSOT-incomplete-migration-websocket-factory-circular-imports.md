# SSOT Gardener Progress: WebSocket Factory Circular Import Dependencies

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1031  
**Created:** 2025-09-14  
**Priority:** P0 - Blocks Golden Path  
**Status:** In Progress - Step 0 Complete

## Problem Statement

**CRITICAL SSOT VIOLATION:** SSOT websocket_manager.py imports from deprecated websocket_manager_factory.py, creating circular import dependencies that block Golden Path user login → AI responses flow.

## Root Cause Analysis

### Primary Issue: Incomplete SSOT Migration
- SSOT file imports from deprecated factory instead of being self-contained
- Creates circular dependency: websocket_manager.py → websocket_manager_factory.py → (back to SSOT components)
- Race conditions during WebSocket initialization can cause user context failures

### Files Affected
1. **`/netra_backend/app/websocket_core/websocket_manager.py`** (SSOT importing deprecated)
   - Lines 22-27: Imports from websocket_manager_factory 
   - Should be self-contained SSOT implementation
   
2. **`/netra_backend/app/websocket_core/websocket_manager_factory.py`** (DEPRECATED)
   - Still being imported by SSOT code
   - Should be eliminated entirely
   
3. **`/netra_backend/app/websocket_core/unified_manager.py`** 
   - Additional WebSocket manager implementation
   - Creates confusion about which manager to use
   
4. **`/netra_backend/app/websocket_core/manager.py`**
   - Compatibility layer adding complexity

## Business Impact
- **Golden Path Blocking:** WebSocket failures prevent user login → AI response flow
- **$500K+ ARR Risk:** Critical user experience degradation
- **Development Velocity:** Complex debugging slows fixes
- **User Isolation Risk:** Multiple managers can breach user boundaries

## Step Progress

### ✅ Step 0: SSOT AUDIT - COMPLETE
- [x] Identified critical WebSocket SSOT violation
- [x] Created GitHub issue #1031
- [x] Created progress tracker
- [x] Committed progress tracker

### ⏳ Step 1: DISCOVER AND PLAN TEST - IN PROGRESS
- [ ] 1.1: Find existing tests protecting WebSocket functionality
- [ ] 1.2: Plan new tests for SSOT compliance validation

### ⏳ Step 2: EXECUTE TEST PLAN
- [ ] Create failing tests that reproduce SSOT violation
- [ ] Validate test coverage of affected components

### ⏳ Step 3: PLAN REMEDIATION
- [ ] Design SSOT migration strategy
- [ ] Plan import elimination from deprecated factory

### ⏳ Step 4: EXECUTE REMEDIATION
- [ ] Remove deprecated imports from websocket_manager.py
- [ ] Migrate required components directly into SSOT
- [ ] Eliminate websocket_manager_factory.py

### ⏳ Step 5: TEST FIX LOOP
- [ ] Validate all tests pass
- [ ] Ensure Golden Path functionality maintained
- [ ] Fix any startup or import issues

### ⏳ Step 6: PR AND CLOSURE
- [ ] Create PR linking to issue
- [ ] Validate Golden Path before merge

## Evidence of SSOT Violation

```python
# websocket_manager.py:22-27 - SSOT importing deprecated factory
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,  # ❌ DEPRECATED - should not be imported by SSOT
    WebSocketConnection,      # ❌ Should be defined in SSOT directly  
    _serialize_message_safely, # ❌ Should be SSOT method
    WebSocketManagerMode      # ❌ Should be SSOT enum
)
```

## Solution Strategy
1. **Extract Dependencies:** Move required components from factory into SSOT websocket_manager.py
2. **Remove Import:** Eliminate import from websocket_manager_factory
3. **Validate Functionality:** Ensure no breaking changes to WebSocket operations
4. **Test Golden Path:** Confirm user login → AI responses flow works
5. **Clean Up:** Remove deprecated factory file entirely

## Next Actions
- Start Step 1: Discover and plan tests with subagent
- Focus on non-docker tests (unit, integration without docker, e2e staging)