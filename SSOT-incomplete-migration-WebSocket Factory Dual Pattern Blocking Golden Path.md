# SSOT-incomplete-migration-WebSocket Factory Dual Pattern Blocking Golden Path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1144  
**Status:** DISCOVERY COMPLETE  
**Priority:** P0 - Blocks Golden Path and enterprise deployment  
**Created:** 2025-09-14  

## Problem Summary
WebSocket Factory Dual Pattern is the most critical SSOT violation blocking Golden Path user flow (login → AI responses). **73 total WebSocket files** split across two incompatible directory structures causing race conditions in user session isolation and factory initialization failures.

## Evidence
### Conflicting Directory Structures
- `/netra_backend/app/websocket/` (5 files) vs `/netra_backend/app/websocket_core/` (67 files)

### Key Files Creating Confusion
- `/netra_backend/app/websocket_core/manager.py` - Compatibility shim
- `/netra_backend/app/websocket_core/websocket_manager.py` - "SSOT" interface  
- `/netra_backend/app/websocket_core/unified_manager.py` - Actual implementation
- `/netra_backend/app/websocket/connection_manager.py` - Legacy compatibility layer

## Business Impact
- **$500K+ ARR at risk** - Chat functionality reliability threatened
- **Enterprise compliance blocked** - User isolation violations prevent HIPAA/SOC2/SEC compliance
- **Golden Path failure** - Users cannot reliably login → get AI responses

## Remediation Plan (TBD)
1. Consolidate to single SSOT WebSocket factory pattern
2. Eliminate dual directory structure
3. Ensure enterprise-grade user isolation
4. Maintain backwards compatibility during migration

## Work Progress

### Step 0: Discovery ✅ COMPLETE
- [x] SSOT audit completed
- [x] GitHub issue created: #1144
- [x] Evidence documented
- [x] Business impact assessed

### Step 1: DISCOVER AND PLAN TEST (NEXT)
- [ ] 1.1 DISCOVER EXISTING: Find collection of existing tests protecting against breaking changes
- [ ] 1.2 PLAN ONLY: Plan for update, align, or creation of required test suites

### Step 2: EXECUTE THE TEST PLAN (PENDING)
- [ ] Create and run new SSOT tests for WebSocket factory pattern

### Step 3: PLAN REMEDIATION OF SSOT (PENDING)
- [ ] Plan SSOT remediation approach

### Step 4: EXECUTE THE REMEDIATION SSOT PLAN (PENDING)
- [ ] Execute the remediation

### Step 5: ENTER TEST FIX LOOP (PENDING)
- [ ] Prove changes maintain system stability
- [ ] Fix any failing tests

### Step 6: PR AND CLOSURE (PENDING)
- [ ] Create PR if tests pass
- [ ] Cross-link issue for closure

## Notes
- **Complexity**: HIGH - 73 files across 2 directory structures requiring careful migration
- **Related Issues**: Issue #1116 SSOT Agent Factory Migration
- **Focus**: Enterprise user isolation and Golden Path reliability