# SSOT-incomplete-migration-MessageRouter-consolidation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/952  
**Created:** 2025-09-14  
**Status:** In Progress  
**Priority:** P0 - CRITICAL  

## Issue Summary

Critical SSOT violation: 4+ duplicate MessageRouter implementations blocking Golden Path user → AI response flow.

## Discovered Violations

### 1. Multiple MessageRouter Implementations (CRITICAL)
- `/netra_backend/app/core/message_router.py` (Lines 55-157)
- `/netra_backend/app/agents/message_router.py` (Lines 8-12) 
- `/netra_backend/app/websocket_core/handlers.py` (Lines 1208-1594)
- `/netra_backend/app/services/websocket/quality_message_router.py` (Lines 36-100+)

### 2. Duplicate WebSocket Event Routing (HIGH)
- `/netra_backend/app/services/websocket_event_router.py` (Lines 41-100+)
- `/netra_backend/app/services/user_scoped_websocket_event_router.py` (Lines 93-100+)

### 3. Message Handler Inconsistencies (HIGH)
- `/netra_backend/app/websocket_core/handlers.py` (Lines 57-1669)
- `/netra_backend/app/services/message_handlers.py` (Lines 81-100+)

## Impact Analysis

**Business Risk:** $500K+ ARR functionality at risk  
**Golden Path Impact:** Message routing confusion prevents reliable chat responses  
**Root Cause:** Incomplete SSOT migration left 14+ MessageRouter implementations

## Process Progress

### ✅ Step 0: SSOT Audit Complete
- [x] Discovered critical MessageRouter SSOT violations
- [x] Created GitHub issue #952
- [x] Created progress tracking file

### 🔄 Step 1: Discover and Plan Test (In Progress)
- [ ] Discover existing tests protecting against breaking changes
- [ ] Plan test updates/creation for SSOT refactor validation
- [ ] Document test strategy in this file

### ⏳ Step 2: Execute Test Plan
- [ ] Create new SSOT validation tests
- [ ] Run and validate test checks

### ⏳ Step 3: Plan Remediation
- [ ] Plan SSOT remediation approach
- [ ] Define migration strategy

### ⏳ Step 4: Execute Remediation
- [ ] Execute MessageRouter SSOT consolidation
- [ ] Implement single source of truth

### ⏳ Step 5: Test Fix Loop
- [ ] Run all tests and fix any failures
- [ ] Validate system stability

### ⏳ Step 6: PR and Closure
- [ ] Create pull request
- [ ] Link to close this issue

## References

- **Existing Analysis:** `reports/SSOT-incomplete-migration-MessageRouter-critical-violations.md`
- **Related Issues:** Issue #217 MessageRouter consolidation
- **Architecture Docs:** See CLAUDE.md for SSOT requirements

## Notes

- Focus on `websocket_core/handlers.py` MessageRouter as SSOT candidate
- Restore 4 broken mission-critical tests  
- 15+ test files have REMOVED_SYNTAX_ERROR comments indicating incomplete migration