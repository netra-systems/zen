# SSOT Gardener Progress: Duplicate Event Broadcasting Functions

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/982
**Priority:** P0 - Critical Golden Path blocker
**Status:** Step 0 Complete - Issue Created

## Problem Summary
Critical SSOT violation in message routing - duplicate `broadcast_to_user()` implementations causing:
- Cross-user event leakage risk
- Golden Path blocking (agent responses may not reach correct connections)
- Race conditions in message delivery

## Files Affected
- `netra_backend/app/services/websocket_event_router.py:198` - `broadcast_to_user(user_id, ...)`
- `netra_backend/app/services/user_scoped_websocket_event_router.py:234` - `broadcast_to_user(...)` (scoped)
- `netra_backend/app/services/user_scoped_websocket_event_router.py:545` - `broadcast_user_event()` (standalone)

## Business Impact
- **Revenue at Risk:** $500K+ ARR dependent on reliable message routing
- **Security Impact:** Cross-user data leakage possible
- **Golden Path Impact:** Core chat functionality affected

## Process Status

### ✅ Step 0: SSOT AUDIT (COMPLETE)
- [x] SSOT audit completed by sub-agent
- [x] Critical violation identified and prioritized
- [x] GitHub issue #982 created
- [x] Progress tracking file created

### 🔄 Step 1: DISCOVER AND PLAN TEST (IN PROGRESS)
- [ ] 1.1 Discover existing tests protecting against breaking changes
- [ ] 1.2 Plan new tests for SSOT refactor validation

### ⏳ Remaining Steps
- [ ] Step 2: Execute test plan (20% new SSOT tests)
- [ ] Step 3: Plan SSOT remediation
- [ ] Step 4: Execute remediation
- [ ] Step 5: Test fix loop
- [ ] Step 6: PR and closure

## Test Plan (To Be Developed)
- Existing test discovery pending
- New SSOT-specific tests pending
- Focus: Non-docker tests (unit, integration, e2e staging)

## Remediation Plan (To Be Developed)
- Consolidation strategy pending
- SSOT pattern selection pending
- Migration approach pending

---
**Last Updated:** 2025-01-14 (Step 0 Complete)
**Next Action:** Step 1 - Discover and Plan Test