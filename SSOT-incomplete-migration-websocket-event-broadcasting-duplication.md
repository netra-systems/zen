# SSOT-incomplete-migration-websocket-event-broadcasting-duplication

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1058

**Created:** 2025-01-14
**Status:** DISCOVERED - PLANNING PHASE
**Priority:** P0 CRITICAL

## Problem Summary
Multiple independent implementations of `broadcast_to_user` functionality creating security vulnerabilities and Golden Path failures.

### Files Involved
- `netra_backend/app/services/websocket_event_router.py` (Lines 198-248)
- `netra_backend/app/services/user_scoped_websocket_event_router.py` (Lines 234-248)
- `netra_backend/app/services/websocket_broadcast_service.py` (SSOT target)

### Business Impact
- **$500K+ ARR at Risk**: Cross-user event leakage
- **Security Breach**: Events reaching wrong users
- **Golden Path Blocked**: Users login → AI responses flow compromised

## SSOT Gardener Process Log

### Step 0: DISCOVER NEXT SSOT ISSUE ✅ COMPLETE
- [x] SSOT audit completed - Critical WebSocket broadcasting duplication identified
- [x] GitHub issue #1058 created
- [x] Local .md tracker created

### Step 1: DISCOVER AND PLAN TEST 🔄 IN PROGRESS
- [ ] 1.1 DISCOVER EXISTING: Find existing tests protecting WebSocket broadcasting
- [ ] 1.2 PLAN ONLY: Plan unit/integration/e2e tests for SSOT refactor

### Step 2: EXECUTE THE TEST PLAN
- [ ] Create 20% new SSOT tests for broadcasting functionality
- [ ] Audit and run test checks (non-docker only)

### Step 3: PLAN REMEDIATION OF SSOT
- [ ] Plan SSOT consolidation strategy for WebSocket broadcasting

### Step 4: EXECUTE THE REMEDIATION SSOT PLAN
- [ ] Execute SSOT remediation

### Step 5: ENTER TEST FIX LOOP
- [ ] 5.1 Run and fix all test cases
- [ ] 5.2 IND_GCIFS_UINF cycles until all tests pass
- [ ] 5.3 Run startup tests (non-docker)

### Step 6: PR AND CLOSURE
- [ ] Create PR with cross-link to issue #1058

## Technical Details

### Current State Analysis
- **3+ broadcast implementations** with different error handling patterns
- **Inconsistent user validation** approaches across implementations
- **Race conditions** in multi-user chat scenarios
- **Conflicting adapter patterns** attempting SSOT consolidation

### SSOT Target
Consolidate to single authoritative implementation in:
`netra_backend/app/services/websocket_broadcast_service.py`

### Security Implications
- Cross-user event contamination
- User isolation failures
- Enterprise security compliance violations

## Next Actions
1. Spawn sub-agent for Step 1.1: Discover existing tests
2. Spawn sub-agent for Step 1.2: Plan test strategy
3. Continue through SSOT Gardener process

---
**Process Status:** Step 0 Complete - Moving to Step 1
**Last Updated:** 2025-01-14