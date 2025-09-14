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

### ⏳ Next Steps  
1. **EXECUTE TEST PLAN** - Create 20% new SSOT validation tests
2. **PLAN REMEDIATION** - Plan safe removal of deprecated factory  
3. **EXECUTE REMEDIATION** - Remove legacy code and update imports
4. **TEST FIX LOOP** - Ensure all tests pass
5. **PR AND CLOSURE** - Create PR and close issue

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