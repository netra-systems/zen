# SSOT Legacy Removal: WebSocket Manager Factory

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1128
**Priority:** P0 CRITICAL - GOLDEN PATH BLOCKER
**Status:** IN PROGRESS - Step 0 Complete

## Issue Summary
Deprecated WebSocket Manager Factory compatibility layer (587 lines) still exists and blocks Golden Path through SSOT fragmentation and race conditions in WebSocket initialization.

## Critical Files
- **PRIMARY:** `/netra_backend/app/websocket_core/websocket_manager_factory.py` (587 lines)
- **DEPENDENT:** `/netra_backend/app/services/unified_authentication_service.py:663` (imports deprecated factory)

## Business Impact
- **Revenue Risk:** $500K+ ARR from WebSocket chat failures
- **User Experience:** Race conditions break real-time chat (90% of platform value)
- **Development Velocity:** Legacy patterns create confusion

## Process Progress

### ✅ 0) SSOT Issue Discovery (COMPLETE)
- [x] Audited codebase for legacy SSOT violations 
- [x] Identified WebSocket Manager Factory as P0 critical blocker
- [x] Created GitHub Issue #1128
- [x] Created local progress tracker (this file)
- [x] Committed initial tracking to git

### ✅ 1) DISCOVER AND PLAN TEST (COMPLETE)
- [x] **1.1 DISCOVER EXISTING:** Found 3,778+ WebSocket-related test files
- [x] Mission critical tests already SSOT compliant (LOW RISK)
- [x] Comprehensive test coverage protecting Golden Path functionality
- [x] Key finding: Only `create_defensive_user_execution_context` needs migration
- [x] **1.2 PLAN TESTING:** 3-phase implementation strategy planned
- [x] Risk assessment: LOW-MEDIUM with clear mitigation path
- [x] Staging validation available for end-to-end testing

### ✅ 2) EXECUTE TEST PLAN (COMPLETE)
- [x] **Created 4 comprehensive test files** with 21 test methods total
- [x] **Import Validation Test:** `test_websocket_factory_import_validation.py` (5 methods)
- [x] **Authentication SSOT Compliance:** `test_authentication_service_ssot_compliance.py` (6 methods)  
- [x] **Factory Deprecation Proof:** `test_websocket_factory_deprecation_proof.py` (6 methods)
- [x] **Golden Path Integration:** `test_golden_path_integration_without_factory.py` (6 methods)
- [x] **All tests SSOT compliant** - use established testing infrastructure
- [x] **Business value protected** - $500K+ ARR Golden Path validation included

### ✅ 3) PLAN REMEDIATION (COMPLETE)
- [x] **3-phase implementation strategy** with atomic rollback procedures
- [x] **Single function migration:** `create_defensive_user_execution_context` to SSOT location
- [x] **Minimal dependencies:** Only 2 primary files need import updates
- [x] **Risk assessment:** LOW-MEDIUM with comprehensive test validation  
- [x] **Target location:** `user_execution_context.py` identified as SSOT home
- [x] **Timeline:** 4-7 hours with zero business impact when executed properly

### ⏳ Next Steps  
1. **EXECUTE REMEDIATION** - Implement 3-phase factory removal
2. **TEST FIX LOOP** - Ensure all tests pass
3. **PR AND CLOSURE** - Create PR and close issue

## Technical Analysis
The websocket_manager_factory.py contains 587 lines of compatibility code that:
1. Creates dual import paths causing initialization race conditions
2. Fragments SSOT architecture with competing patterns  
3. Actively used by unified_authentication_service.py preventing clean removal
4. Blocks full migration to modern SSOT WebSocket patterns

## Success Criteria
- [ ] Remove deprecated websocket_manager_factory.py entirely
- [ ] Update all imports to use SSOT WebSocket patterns
- [ ] Validate Golden Path WebSocket functionality remains intact
- [ ] All related tests pass after migration
- [ ] No regression in $500K+ ARR chat functionality

## Test Strategy (TBD)
- Identify existing WebSocket tests that must continue passing
- Create new SSOT compliance tests
- Validate Golden Path user flow remains functional
- Test real-time chat event delivery

---
*Started: 2025-09-14*
*Agent Session: SSOT Gardener - Removing Legacy*