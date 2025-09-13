# SSOT-incomplete-migration-websocket-notifier-duplicate

**GitHub Issue:** [#669](https://github.com/netra-systems/netra-apex/issues/669)
**Priority:** P0 CRITICAL
**Status:** In Progress - SSOT Audit Complete
**Created:** 2025-09-12

## Business Impact Assessment
- **Revenue at Risk**: $500K+ ARR
- **Platform Impact**: 90% of business value depends on reliable chat functionality
- **Golden Path Status**: ❌ **PARTIALLY BLOCKED** - Inconsistent event delivery risk

## SSOT Violations Identified

### 1. P0 CRITICAL: Duplicate WebSocketNotifier Implementation
- **File**: `scripts/websocket_notifier_rollback_utility.py`
- **Issue**: Legacy rollback utility contains duplicate WebSocketNotifier
- **Risk**: Conflicts with SSOT implementation, could break agent event delivery
- **Golden Path Impact**: BLOCKING - Critical for user login → AI response flow

### 2. P1 HIGH: Multiple ExecutionEngineFactory Patterns
- **Issue**: Inconsistent agent factory implementations across codebase
- **Impact**: Development confusion, potential race conditions
- **Golden Path Impact**: DEGRADING - Affects agent initialization reliability

## Critical Agent Events at Risk
The following 5 business-critical WebSocket events must work reliably:
1. `agent_started` - User sees agent began processing
2. `agent_thinking` - Real-time reasoning visibility
3. `tool_executing` - Tool usage transparency
4. `tool_completed` - Tool results display
5. `agent_completed` - User knows response is ready

## Process Progress

### ✅ Step 0: SSOT Audit Complete (2025-09-12)
- [x] Comprehensive audit of agent events SSOT violations
- [x] Priority assessment based on Golden Path impact
- [x] GitHub issue created: #669
- [x] Business risk assessment: $500K+ ARR at risk

### 🔄 Step 1: Test Discovery & Planning (Next)
- [ ] Discover existing tests protecting WebSocket event delivery
- [ ] Plan test suite for SSOT remediation validation
- [ ] Focus on mission critical WebSocket agent events suite

### ⏳ Upcoming Steps
- [ ] Step 2: Execute test plan for new SSOT tests
- [ ] Step 3: Plan SSOT remediation strategy
- [ ] Step 4: Execute SSOT remediation
- [ ] Step 5: Test fix loop - prove system stability
- [ ] Step 6: Create PR and close issue

## Test Strategy

### Existing Critical Tests to Validate
- `python tests/mission_critical/test_websocket_agent_events_suite.py`
- `python netra_backend/tests/critical/test_websocket_state_regression.py`
- `python tests/e2e/test_websocket_dev_docker_connection.py`

### New Tests Required (20% of work)
- SSOT WebSocketNotifier validation tests
- Agent event delivery consistency tests
- Factory pattern consolidation tests

### Test Execution Constraints
- ONLY run tests that don't require Docker
- Use unit, integration (no docker), or e2e on staging GCP remote
- 60% existing tests validation, 20% new SSOT tests, 20% validation

## Remediation Strategy (Planning Phase)

### Immediate Actions Required
1. **Remove Duplicate**: Delete `scripts/websocket_notifier_rollback_utility.py`
2. **Validate SSOT**: Confirm SSOT WebSocketNotifier in `/netra_backend/app/websocket_core/`
3. **Consolidate Factories**: Unify ExecutionEngineFactory implementations
4. **Update Documentation**: Reflect actual vs claimed SSOT completion status

### Success Criteria
- [ ] Duplicate WebSocketNotifier removed from rollback utility
- [ ] SSOT WebSocketNotifier validates all 5 critical events
- [ ] All mission critical tests pass
- [ ] Golden Path user flow works end-to-end
- [ ] No regression in existing functionality

## Risk Mitigation
- Atomic commits for each remediation step
- Test validation before each commit
- Rollback plan if stability issues discovered
- Focus on Golden Path preservation throughout

---

**Next Action:** Spawn sub-agent for Step 1 - Test Discovery & Planning