# SSOT-incomplete-migration-agent-factory-singleton-legacy

**GitHub Issue:** #709
**Priority:** P0 CRITICAL
**Focus Area:** agents
**Status:** Working on remediation

## Problem Summary
Legacy singleton patterns remain in agent factory system causing:
- Cross-user state contamination
- WebSocket event delivery failures
- Race conditions in multi-user scenarios
- Global state preventing proper user isolation

## Critical Files Identified
- `netra_backend/app/agents/supervisor/agent_instance_factory.py`
- `netra_backend/app/agents/supervisor/execution_engine_factory.py`
- Multiple SupervisorAgent implementations detected
- Inconsistent UserExecutionContext usage

## SSOT Violations Found by Audit
1. **P0 - Duplicate SupervisorAgent implementations** (3 variants causing inconsistent behavior)
2. **P0 - Legacy singleton patterns** in agent factories
3. **P0 - UserExecutionContext isolation failures** (user data contamination risk)
4. **P1 - Inconsistent factory patterns** across agent types
5. **P1 - Mixed initialization patterns** (factory vs direct instantiation)

## Progress Tracking

### Phase 0: Discovery ✅
- [x] SSOT audit completed
- [x] Issue #709 identified as target
- [x] Local tracking file created

### Phase 1: Test Discovery and Planning ✅
- [x] Discover existing tests protecting agent factories (**23 critical tests identified**)
- [x] Plan new SSOT validation tests (**6 new test files planned, 30-42h effort**)
- [x] Plan user isolation validation tests (**Cross-user contamination focus**)

#### Test Discovery Results:
- **23 Critical Tests** must continue passing during SSOT refactor
- **80%+ coverage** in factory patterns, user isolation, WebSocket integration
- **Key gaps:** Cross-user contamination testing, singleton vs factory validation

#### New Test Plan:
- **60% Unit tests** (no Docker) - Fast development feedback
- **30% Integration tests** (selective services) - Real-world validation
- **10% E2E Staging tests** - Business value protection
- **Strategy:** 20% failing tests (prove violations) + 60% validation + 20% performance

### Phase 2: Test Creation ✅
- [x] Create failing tests for SSOT violations (**10 tests in 3 files**)
- [x] Create user isolation validation tests (**Cross-user contamination exposed**)
- [x] Validate test execution (no docker required) (**All 10 tests fail as expected**)

#### Test Creation Results:
- **`test_ssot_user_contamination_violations.py`** (3 tests) - Cross-user factory/WebSocket contamination
- **`test_ssot_supervisor_duplication_violations.py`** (3 tests) - Multiple SupervisorAgent implementations
- **`test_ssot_factory_singleton_violations.py`** (4 tests) - Factory returning singletons instead of unique instances

#### Major Discovery:
- **3 SupervisorAgent implementations found:** `supervisor_ssot.py`, `supervisor_consolidated.py`, `chat_orchestrator_main.py`
- **Agent Registry Configuration:** Singleton registry breaks multi-user isolation
- **WebSocket Bridge Sharing:** Events delivered to wrong users
- **100% failure rate:** All 10 tests fail as expected, proving violations exist

### Phase 3: SSOT Remediation Planning ✅
- [x] Plan singleton removal strategy (**4-phase approach: A-D over 7 weeks**)
- [x] Plan factory pattern consolidation (**Interface standardization + consumer migration**)
- [x] Plan UserExecutionContext standardization (**Per-user registry patterns**)

#### SSOT Remediation Strategy:
**Phase A (Weeks 1-2):** SupervisorAgent Consolidation
- Establish `supervisor_ssot.py` as canonical SSOT implementation
- Migrate 140+ consumers from `supervisor_consolidated.py` (10-15 files/day)
- Standardize interfaces, eliminate duplicate methods

**Phase B (Weeks 3-4):** Agent Registry De-Singletonization
- Replace global AgentRegistry singleton with factory pattern
- Implement UserExecutionContext-scoped registries
- Ensure complete user isolation

**Phase C (Weeks 5-6):** WebSocket Bridge Isolation
- Leverage existing UnifiedWebSocketEmitter SSOT implementation
- Ensure event delivery isolation per UserExecutionContext
- Validate no cross-user event contamination

**Phase D (Week 7):** Final Factory Pattern Compliance
- Standardize all factory interfaces across agent types
- Complete SSOT compliance validation

### Phase 4: Execute Remediation 🔄
- [ ] Remove legacy singleton patterns
- [ ] Consolidate SupervisorAgent implementations
- [ ] Fix UserExecutionContext violations

### Phase 5: Test Validation Loop 🔄
- [ ] Run all existing tests
- [ ] Run new SSOT validation tests
- [ ] Fix any breaking changes
- [ ] Validate Golden Path functionality

### Phase 6: PR and Closure 🔄
- [ ] Create PR when all tests pass
- [ ] Link to issue #709 for auto-close
- [ ] Validate staging deployment

## Business Impact
- **Revenue Risk:** $500K+ ARR from chat functionality
- **Golden Path:** Blocks user login → AI responses
- **User Safety:** Cross-user state contamination prevention