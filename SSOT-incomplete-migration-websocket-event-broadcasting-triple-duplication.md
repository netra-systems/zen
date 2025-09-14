# SSOT-incomplete-migration-websocket-event-broadcasting-triple-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1014
**Created:** 2025-01-14
**Status:** DISCOVERY COMPLETE
**Priority:** P0 - Golden Path Blocker

## Problem Statement

Critical SSOT violation: Three separate WebSocket event broadcasting implementations violate SSOT principles and create debugging loops preventing reliable AI response delivery.

## Files Involved

### Duplicate Broadcasting Logic
1. `/netra_backend/app/services/websocket_event_router.py` (lines 198-279) - Legacy singleton
2. `/netra_backend/app/services/user_scoped_websocket_event_router.py` (lines 234-327) - User-scoped version
3. `/netra_backend/app/services/websocket_broadcast_service.py` (lines 108-206) - "SSOT" version

## Business Impact
- **Golden Path Blocker:** Users may not receive AI responses reliably
- **Security Risk:** Events may be delivered to wrong users
- **Reliability Issue:** Events may be silently dropped
- **Development Impact:** Creates infinite debugging loops due to fallback logic
- **Revenue Impact:** $500K+ ARR at risk from unreliable chat functionality

## SSOT Analysis
- Issue #982 attempted consolidation but left legacy fallback code
- Three different `broadcast_to_user()` implementations exist
- Inconsistent behavior depending on code path taken
- Violates SSOT principle of single authoritative implementation

## Process Status

### ✅ Step 0: DISCOVERY COMPLETE
- [x] SSOT audit completed
- [x] GitHub issue created: #1014
- [x] Critical violations identified and ranked
- [x] Progress document created

### 🔄 Step 1: DISCOVER AND PLAN TEST (IN PROGRESS)
- [ ] 1.1 DISCOVER EXISTING: Find existing WebSocket broadcasting tests
- [ ] 1.2 PLAN ONLY: Plan test updates/creation for SSOT consolidation

### ⏳ Step 2: EXECUTE TEST PLAN
- [ ] Create new SSOT validation tests
- [ ] Run failing tests to reproduce violations

### ⏳ Step 3: PLAN REMEDIATION
- [ ] Plan SSOT consolidation approach
- [ ] Identify migration path from triple implementation to single

### ⏳ Step 4: EXECUTE REMEDIATION
- [ ] Implement SSOT consolidation
- [ ] Remove legacy fallback logic
- [ ] Update all consumers to use canonical implementation

### ⏳ Step 5: TEST FIX LOOP
- [ ] Validate all tests pass
- [ ] Fix any breaking changes
- [ ] Ensure system stability maintained

### ⏳ Step 6: PR AND CLOSURE
- [ ] Create PR with fixes
- [ ] Link to close issue #1014

## Test Requirements

### Existing Tests to Validate
- Mission critical WebSocket event tests
- User isolation tests
- Event delivery reliability tests
- Golden Path user flow tests

### New Tests Needed
- SSOT broadcasting validation
- Cross-user event contamination prevention
- Fallback logic elimination verification
- Single source of truth compliance

## Success Criteria
- [ ] Single canonical WebSocket broadcasting implementation
- [ ] All legacy implementations removed or delegating to SSOT
- [ ] No fallback logic causing debugging loops
- [ ] All WebSocket events route through canonical service
- [ ] Tests validate reliable event delivery
- [ ] Golden Path user flow restored to 100% reliability

## Notes
- Focus on Golden Path: users login → get AI responses
- FIRST DO NO HARM: ensure changes maintain system stability
- Limit scope to atomic unit addressing broadcasting duplication
- Follow CLAUDE.md SSOT compliance requirements