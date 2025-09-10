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

### Step 1: DISCOVER AND PLAN TEST ✅ COMPLETED
- [x] 1.1 DISCOVER EXISTING: Found 657 WebSocket/event test files with comprehensive coverage
  - Mission Critical Suite: `test_websocket_agent_events_suite.py` (33,111 tokens)
  - Golden Path tests covering login → AI responses
  - All 5 critical events covered: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
  - **GAP IDENTIFIED:** No SSOT source validation or multiple emitter conflict tests
- [x] 1.2 PLAN ONLY: Comprehensive SSOT consolidation test plan created
  - Phase 1: Pre-consolidation failing tests to prove race conditions
  - Phase 2: Consolidation validation ensuring business value
  - Phase 3: Post-consolidation verification

## Test Plan Details
### Critical Tests to Create
1. `test_multiple_emitter_race_condition_reproduction` - MUST FAIL (proves issue)
2. `test_event_source_validation_fails_with_duplicates` - MUST FAIL (proves duplicates)
3. `test_unified_emitter_ssot_compliance` - Validates single source
4. `test_emitter_consolidation_preserves_golden_path` - Business value protection
5. `test_no_race_conditions_single_emitter` - Proves fix works
6. `test_single_emitter_performance_validation` - Performance maintained

### Step 2: EXECUTE THE TEST PLAN ✅ COMPLETED
- [x] Created 6 critical SSOT tests for consolidated event emitter
  - **22 tests total** collected across 6 test modules in `/tests/mission_critical/websocket_emitter_consolidation/`
  - Added missing pytest markers to enable test collection
  - Fixed import issues with WebSocketGoldenPathHelper
  - All tests can now be collected and are ready for execution

## Test Suite Created
### Phase 1: Pre-Consolidation (MUST FAIL - proves issues exist)
- `test_multiple_emitter_race_condition_reproduction.py` (3 tests)
- `test_event_source_validation_fails_with_duplicates.py` (4 tests)

### Phase 2: Consolidation Validation (PASS after consolidation)
- `test_unified_emitter_ssot_compliance.py` (4 tests)
- `test_emitter_consolidation_preserves_golden_path.py` (3 tests)

### Phase 3: Post-Consolidation Verification (PASS after consolidation)
- `test_no_race_conditions_single_emitter.py` (4 tests)
- `test_single_emitter_performance_validation.py` (4 tests)

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