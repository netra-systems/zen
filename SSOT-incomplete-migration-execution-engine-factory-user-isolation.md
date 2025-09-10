# SSOT-incomplete-migration-execution-engine-factory-user-isolation

**GitHub Issue:** [#183](https://github.com/netra-systems/netra-apex/issues/183)  
**Status:** 🔍 Discovery Complete - Planning Tests  
**Created:** 2025-09-10  
**Priority:** CRITICAL - Blocks Golden Path

## Problem Summary

Incomplete singleton-to-factory pattern migration in ExecutionEngine causing critical user isolation failures that block the Golden Path (users login → get AI responses).

### Critical Impact
- **Business Value Loss:** 90% of platform value (chat functionality) compromised
- **User Isolation Failures:** Cross-user data leakage (GDPR/SOC 2 violations)
- **Factory Pattern Tests:** 0/3 passing (0% - all failing)
- **Race Conditions:** 8 detected in AgentExecutionRegistry isolation

## Key Files Identified

### Core Problem Files
- `/netra_backend/app/agents/supervisor/execution_engine_factory.py` - Factory exists but incomplete
- `/netra_backend/app/services/user_execution_context.py` - User context isolation gaps
- `/tests/mission_critical/golden_path/test_agent_state_isolation_never_fail.py` - All tests failing

### Documentation
- `/SPEC/learnings/singleton_removal_phase2_20250902_084436.xml` - 347 lines detailing incomplete migration

## SSOT Violation Analysis

**Root Cause:** Phase 2 singleton removal migration stopped mid-implementation
- ExecutionEngine factory methods return shared instances instead of isolated ones
- WebSocket event delivery broken - UnifiedToolExecutionEngine has null websocket_notifier  
- AgentExecutionRegistry not properly isolated between users
- User execution contexts not fully integrated with factory pattern

## Process Status

### ✅ Step 0: SSOT AUDIT COMPLETE
- [x] Critical violation identified: incomplete-migration
- [x] GitHub issue created: #183
- [x] Impact assessment: CRITICAL - blocks Golden Path
- [x] Files mapped and analyzed

### ✅ Step 1: DISCOVER AND PLAN TESTS  
- [x] 1.1: Discover existing tests protecting against breaking changes
- [x] 1.2: Plan new SSOT-focused tests (20% of effort)

#### 1.1 Test Discovery Results
**GOLD STANDARD TEST:** `/tests/mission_critical/golden_path/test_agent_state_isolation_never_fail.py`
- Legal/compliance-grade user isolation (15 concurrent users)
- **Status:** Likely failing - MUST pass after SSOT fix
- **Priority:** Highest - legal compliance requirement

**REPRODUCTION TESTS (Should start passing):**
- `/tests/integration/test_execution_engine_factory_delegation.py` - Broken factory handoff
- Factory SSOT violation tests - Currently detecting over-engineering

**PROTECTION TESTS (Must keep passing):**
- User execution context isolation tests (~60% currently passing)
- Multi-user WebSocket event isolation tests  
- Concurrent agent state management tests

**Coverage Assessment:** Strong user isolation foundation, weak factory pattern protection

#### 1.2 New SSOT Test Plan (5 Tests - 20% of effort)
**NEW TESTS (Should FAIL before, PASS after factory implementation):**

1. **`test_execution_engine_factory_user_isolation_unit.py`** - PRIORITY 1
   - Factory creates unique instances per user (no shared state)
   - Memory isolation between concurrent user engines
   - Legal compliance: prevents user data leakage

2. **`test_execution_engine_factory_websocket_integration.py`** - PRIORITY 2  
   - Factory-created engines emit events to correct users only
   - Per-user WebSocketNotifier from factory integration
   - Chat functionality: 90% of platform value protection

3. **`test_user_execution_context_factory_integration_unit.py`** - PRIORITY 1
   - Factory validates UserExecutionContext before creation
   - Factory cleanup when user sessions end
   - Context immutability in factory-created engines

4. **`test_execution_engine_ssot_factory_compliance_integration.py`** - PRIORITY 2
   - Factory is ONLY source for ExecutionEngine instances
   - No duplicate creation patterns exist
   - SSOT compliance validation

5. **`test_execution_engine_factory_resource_limits_unit.py`** - PRIORITY 2
   - Factory enforces max engines per user
   - Resource cleanup when limits exceeded
   - Platform stability under load

### 🔄 Current Step
- [ ] Step 2: Execute new test creation
- [ ] Step 3: Plan SSOT remediation  
- [ ] Step 4: Execute SSOT remediation
- [ ] Step 5: Test fix loop until all pass
- [ ] Step 6: PR and closure

## Next Actions
1. Spawn sub-agent to discover existing factory/isolation tests
2. Plan test suite for validating SSOT factory implementation  
3. Focus on tests that don't require Docker (unit, integration non-docker, e2e staging)

## Notes
- This is the #1 priority SSOT violation blocking Golden Path
- User isolation failures create legal/compliance risks
- Factory pattern implementation must be completed atomically
- WebSocket event delivery critical for chat functionality (90% of business value)