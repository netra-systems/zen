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

### ✅ Step 1: DISCOVER AND PLAN TEST (COMPLETE)
- [x] 1.1 Discovered existing tests that use broadcast functions
- [x] 1.2 Comprehensive test plan created and documented
- [x] 1.3 First SSOT compliance test suite implemented

### 🔄 Step 2: Execute Test Plan (IN PROGRESS)
- [x] 2.1 Create SSOT compliance detection tests (unit tests)
- [ ] 2.2 Create function consistency validation tests (integration tests)
- [ ] 2.3 Create user isolation security tests (integration tests)
- [ ] 2.4 Create Golden Path integration tests (e2e staging tests)
- [ ] 2.5 Validate all tests FAIL as expected (detecting SSOT violations)

### ⏳ Remaining Steps
- [ ] Step 3: Plan SSOT remediation
- [ ] Step 4: Execute remediation
- [ ] Step 5: Test fix loop
- [ ] Step 6: PR and closure

## Test Plan ✅ COMPLETE
**Comprehensive Test Strategy:** [`TEST_PLAN_ISSUE_982_SSOT_BROADCAST_DUPLICATES.md`](TEST_PLAN_ISSUE_982_SSOT_BROADCAST_DUPLICATES.md)

### Test Coverage:
- **Unit Tests:** SSOT compliance detection and function discovery
- **Integration Tests:** Function consistency and user isolation security
- **E2E Tests:** Golden Path agent event delivery validation
- **Expected Behavior:** All tests FAIL initially, PASS after SSOT remediation

### Test Files Created:
- `tests/unit/websocket/test_broadcast_function_ssot_compliance.py` ✅ CREATED

### Test Execution Commands:
```bash
# Unit SSOT compliance tests
python -m pytest tests/unit/websocket/test_broadcast_function_ssot_compliance.py -v

# All broadcast SSOT tests (when complete)
python -m pytest -k "broadcast" -v --real-services
```

## Remediation Plan (To Be Developed)
- **Target Functions:** 3 duplicates identified at specific line numbers
- **Consolidation Strategy:** Single canonical broadcast function required
- **Migration Approach:** Maintain backward compatibility during transition
- **SSOT Pattern:** Factory-based user-scoped broadcast router

---
**Last Updated:** 2025-01-14 (Step 1 Complete - Test Plan Ready)
**Next Action:** Step 2 - Execute Test Plan (Create remaining test suites)