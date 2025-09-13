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

### Phase 2: Test Creation 🔄
- [ ] Create failing tests for SSOT violations
- [ ] Create user isolation validation tests
- [ ] Validate test execution (no docker required)

### Phase 3: SSOT Remediation Planning 🔄
- [ ] Plan singleton removal strategy
- [ ] Plan factory pattern consolidation
- [ ] Plan UserExecutionContext standardization

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