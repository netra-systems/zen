# SSOT-incomplete-migration-WebSocket Event Emitter Consolidation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/200  
**Priority:** CRITICAL  
**Business Impact:** $500K+ ARR at risk from WebSocket event delivery failures

## Problem Summary
Multiple WebSocket event emitters create race conditions blocking Golden Path user flow (login → AI responses).

## Duplicate Implementations Found
1. `/netra_backend/app/websocket_core/unified_emitter.py:137`
2. `/netra_backend/app/services/agent_websocket_bridge.py:1752`  
3. `/netra_backend/app/agents/base_agent.py:933`
4. `/netra_backend/app/services/websocket/transparent_websocket_events.py:292`

## Critical Events
- agent_started
- agent_thinking
- tool_executing
- tool_completed
- agent_completed

## Progress Tracking

### Step 1: DISCOVER AND PLAN TEST
- [ ] 1.1 DISCOVER EXISTING: Find existing tests protecting WebSocket event functionality
- [ ] 1.2 PLAN ONLY: Plan tests for SSOT event emitter consolidation

### Step 2: EXECUTE THE TEST PLAN
- [ ] Create new SSOT tests for consolidated event emitter

### Step 3: PLAN REMEDIATION
- [ ] Plan SSOT remediation for WebSocket event emitters

### Step 4: EXECUTE REMEDIATION
- [ ] Implement consolidated SSOT event emitter
- [ ] Update all references to use single source

### Step 5: TEST FIX LOOP
- [ ] Run all tests and fix any issues
- [ ] Verify no breaking changes

### Step 6: PR AND CLOSURE
- [ ] Create PR linking to issue #200
- [ ] Close issue on successful merge

## Technical Notes
- Target implementation: `/netra_backend/app/websocket_core/ssot_event_emitter.py`
- Must maintain Golden Path functionality
- All tests must pass before PR creation