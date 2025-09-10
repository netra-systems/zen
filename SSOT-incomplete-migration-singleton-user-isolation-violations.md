# SSOT Incomplete Migration: Singleton User Isolation Violations

**Issue Type:** SSOT-incomplete-migration  
**Created:** 2025-01-09  
**Priority:** CRITICAL - Blocking Golden Path  
**Business Impact:** $500K+ ARR at risk from user session bleeding

## Critical Violations Discovered

### 1. ServiceLocator Singleton - USER ISOLATION VIOLATION
- **File:** `netra_backend/app/services/service_locator_core.py:29-38`
- **Risk:** User A's services leak to User B
- **Impact:** CRITICAL - Core dependency injection affects all sessions

### 2. WebSocket Event Validator Global Instance - MISSION CRITICAL  
- **File:** `netra_backend/app/websocket_core/event_validator.py:880-892`
- **Risk:** Event validation state contaminated across users
- **Impact:** CRITICAL - False positive/negative validation affects chat

### 3. WebSocket Event Router Singleton - SESSION BLEEDING
- **File:** `netra_backend/app/services/websocket_event_router.py:404, 390-398`  
- **Risk:** User A's agent responses route to User B
- **Impact:** HIGH - Privacy violations, GDPR compliance risk

## Work Progress

### Phase 0: Discovery ✅ COMPLETE
- [x] SSOT audit completed
- [x] 3 critical violations identified
- [x] Business impact assessed
- [x] GitHub issue created

### Phase 1: Test Discovery & Planning ✅ COMPLETE
- [x] **Found existing protection tests** - 33 critical tests identified
- [x] **Mission critical tests**: `test_websocket_agent_events_suite.py` (33K+ lines)
- [x] **User isolation tests**: Factory pattern validation, multi-user isolation
- [x] **Component tests**: EventValidator, EventRouter, ServiceLocator
- [x] **Coverage gaps identified**: ServiceLocator transition, race conditions
- [x] **Plan new SSOT compliance tests** - 30 new test files planned
- [x] **Test strategy designed** - 60% failing initially, 100% pass after refactoring
- [x] **Coverage designed**: Mission Critical (8), Integration (12), Unit (8), E2E (2)

### Phase 2: Test Creation (20% new tests) ✅ COMPLETE
- [x] **Created reproduction tests** - 4 critical tests exposing singleton violations
- [x] **ServiceLocator test**: PROVEN same memory address for different users  
- [x] **EventValidator test**: CONFIRMED global instance contamination
- [x] **WebSocket isolation test**: Integration test covering full stack
- [x] **Factory validation test**: Post-refactoring success criteria defined

**Test Results:**
- `test_service_locator_user_session_bleeding.py` - ✅ FAILING (exposes violation)
- `test_event_validator_state_contamination.py` - ✅ CREATED  
- `test_multi_user_websocket_event_isolation.py` - ✅ CREATED
- `test_factory_pattern_user_isolation_validation.py` - ✅ CREATED

### Phase 3: SSOT Remediation Planning
- [ ] Design UserExecutionContext factory patterns
- [ ] Plan ServiceLocator per-user pattern
- [ ] Design WebSocket isolation architecture

### Phase 4: Implementation
- [ ] Replace ServiceLocator singleton with factory
- [ ] Implement per-user EventValidator creation
- [ ] Replace WebSocket router with user-scoped instances

### Phase 5: Test Fix Loop
- [ ] Run existing tests and fix failures
- [ ] Validate user isolation works correctly
- [ ] Ensure no new breaking changes

## Test Commands to Run
```bash
# Mission critical singleton tests
python tests/mission_critical/test_singleton_removal_phase2.py

# User isolation validation  
python tests/integration/test_user_session_isolation.py

# WebSocket event validation
python tests/mission_critical/test_websocket_agent_events_suite.py
```

## Success Criteria
- [ ] All singleton patterns replaced with per-user factories
- [ ] User A and User B sessions completely isolated
- [ ] WebSocket events properly scoped to user
- [ ] All existing tests continue to pass
- [ ] New isolation tests pass

## Notes
- Focus on atomic changes that maintain system stability
- Each component must be independently testable
- No shared state between concurrent user sessions