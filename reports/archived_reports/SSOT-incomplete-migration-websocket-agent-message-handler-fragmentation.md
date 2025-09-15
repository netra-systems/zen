# SSOT-incomplete-migration-websocket-agent-message-handler-fragmentation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1093
**Created:** 2025-09-14
**Status:** DISCOVERY COMPLETE
**Priority:** CRITICAL - Blocking Golden Path ($500K+ ARR)

## Problem Summary

Multiple WebSocket message handler implementations are creating agent communication fragmentation, directly preventing reliable user-to-AI message flow in the golden path workflow.

## Critical SSOT Violations Discovered

### 1. Multiple WebSocket Message Handlers
- **File 1:** `websocket_core/agent_handler.py` - Agent-specific message handler
- **File 2:** `services/websocket/message_handler.py` - Queue-based message handler
- **File 3:** `websocket_core/handlers.py` - Multiple built-in handlers
- **Conflict:** All handle same message types (`START_AGENT`, `USER_MESSAGE`, `CHAT`) with different logic

### 2. Factory Pattern Duplication
- **Active:** `websocket_core/websocket_manager.py` (canonical)
- **Deprecated but Active:** `websocket_core/websocket_manager_factory.py`
- **Impact:** Dual initialization paths breaking user isolation

### 3. Agent Execution Engine Fragmentation
- Multiple execution engine implementations potentially causing cross-user state contamination

## Business Impact Analysis

**Golden Path Blockage:**
- Message routing conflicts prevent reliable user → AI communication
- WebSocket event fragmentation causes inconsistent agent progress updates
- User isolation violations risk data contamination between concurrent users
- Agent execution failures leave users without responses

**ARR Risk:** $500K+ revenue dependent on reliable chat functionality

## Root Cause

Incomplete migration from monolithic message handling to modular handler architecture. Instead of eliminating duplicates during SSOT consolidation, overlapping implementations were created.

## Success Criteria

✅ Single canonical agent message handler
✅ Deprecated factory patterns completely removed
✅ One execution engine path for agent processing
✅ Integration tests validating complete golden path message flow
✅ All existing tests continue to pass
✅ New tests reproducing and validating SSOT fixes

## Progress Log

### Step 0: DISCOVERY COMPLETE ✅
- [x] SSOT audit completed
- [x] GitHub issue created: #1093
- [x] Local tracker created
- [x] Initial commit made

### Next Steps
- [ ] Step 1: Discover and Plan Tests (SNST)
- [ ] Step 2: Execute Test Plan (SNST)
- [ ] Step 3: Plan Remediation (SNST)
- [ ] Step 4: Execute Remediation (SNST)
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Files for Remediation

**Primary SSOT Consolidation Target:**
- `websocket_core/agent_handler.py`
- `services/websocket/message_handler.py`
- `websocket_core/handlers.py`
- `websocket_core/websocket_manager_factory.py` (REMOVE)

**Supporting Files:**
- Agent execution engines (identify and consolidate)
- WebSocket event dispatching logic
- Message routing configuration

## Test Requirements

**Existing Tests to Validate:**
- Mission critical WebSocket tests
- Golden path integration tests
- Agent execution tests
- User isolation tests

**New Tests to Create:**
- SSOT message handler validation
- WebSocket event consistency tests
- Agent communication integration tests
- User isolation under concurrent load

---

*This file tracks progress on SSOT violation remediation. Updated after each major step.*