# SSOT-incomplete-migration-eventvalidator-consolidation

## Issue Details
- **GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/214
- **Branch:** develop-long-lived  
- **Created:** 2025-09-10
- **Status:** DISCOVERY_COMPLETE → PLANNING_TESTS

## SSOT Audit Results

### Critical Findings
**25+ duplicate EventValidator implementations** causing inconsistent WebSocket event validation for golden path.

### Primary SSOT Violation
- **Production:** `/netra_backend/app/services/websocket_error_validator.py` (398 lines)
- **SSOT Framework:** `/test_framework/ssot/agent_event_validators.py` (458 lines)  
- **20+ Test Duplicates:** Custom validators in tests with different logic

### Business Impact
- **Revenue Risk:** $500K+ ARR chat functionality unreliable
- **Golden Path Blocked:** Inconsistent validation of 5 critical events
- **Silent Failures:** Different error handling patterns across validators

### Files Requiring Attention
1. `/netra_backend/app/services/websocket_error_validator.py` - DELETE, use SSOT
2. `/test_framework/ssot/agent_event_validators.py` - ENHANCE as primary SSOT
3. All test files with custom EventValidator classes - MIGRATE to SSOT

## Process Progress

### ✅ 0) DISCOVER NEXT SSOT ISSUE (COMPLETE)
- ✅ SSOT audit completed
- ✅ GitHub issue #214 created
- ✅ Local tracking file created

### 🔄 1) DISCOVER AND PLAN TEST (IN_PROGRESS)
- [ ] 1.1) DISCOVER EXISTING: Find existing tests protecting against breaking changes
- [ ] 1.2) PLAN ONLY: Plan update/creation of test suites for SSOT refactor

### ⏸️ 2) EXECUTE THE TEST PLAN
### ⏸️ 3) PLAN REMEDIATION OF SSOT  
### ⏸️ 4) EXECUTE THE REMEDIATION SSOT PLAN
### ⏸️ 5) ENTER TEST FIX LOOP
### ⏸️ 6) PR AND CLOSURE

## Next Actions
1. Spawn sub-agent to discover existing tests protecting EventValidator functionality
2. Plan new SSOT tests to validate consolidation
3. Execute test plan before remediation