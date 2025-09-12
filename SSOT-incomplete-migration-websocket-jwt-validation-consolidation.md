# SSOT-incomplete-migration-websocket-jwt-validation-consolidation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/525  
**Priority:** P0 - CRITICAL  
**Status:** DISCOVERED  
**Focus Area:** websockets auth SSOT violations

## Problem Summary

**Business Impact:** BLOCKS $500K+ ARR - Users cannot login → get AI responses due to WebSocket authentication failures

### SSOT Violations Identified

Multiple JWT validation implementations across WebSocket authentication stack creating cascade SSOT violations:

1. **`/netra_backend/app/websocket_core/user_context_extractor.py`** (Lines 184-238)
   - Custom JWT validation with fallback patterns
   - Uses both UnifiedAuthInterface AND AuthServiceClient

2. **`/netra_backend/app/websocket_core/unified_websocket_auth.py`** (Lines 39-44)  
   - Claims to be SSOT but delegates to UnifiedAuthenticationService
   - Has own error handling logic

3. **`/netra_backend/app/auth_integration/auth.py`** (Lines 117-194)
   - Direct AuthServiceClient JWT validation with token reuse tracking
   - Independent validation logic

4. **`/auth_service/auth_core/core/jwt_handler.py`** (Lines 109-240)
   - Canonical auth service JWT validation 
   - Different security checks from other modules

### Golden Path Impact

- **Authentication race conditions** in WebSocket handshake
- **WebSocket 1011 errors** blocking chat functionality  
- **Inconsistent JWT secret/validation** across modules
- **User login → AI responses flow** broken

## Resolution Plan

**SSOT Consolidation Strategy:**
1. Designate `jwt_handler.py` as CANONICAL JWT validation source
2. Remove JWT logic from `user_context_extractor.py` and `unified_websocket_auth.py`
3. Standardize all modules to use AuthServiceClient → jwt_handler.py chain
4. Eliminate fallback validation patterns creating SSOT violations

## Work Progress

- [x] **STEP 0:** SSOT audit completed - Critical P0 violation identified
- [x] **STEP 0.2:** GitHub issue #525 created and local tracking file established
- [ ] **STEP 1:** Discover and plan tests for SSOT violations
- [ ] **STEP 2:** Execute test plan for new SSOT tests  
- [ ] **STEP 3:** Plan SSOT remediation
- [ ] **STEP 4:** Execute SSOT remediation plan
- [ ] **STEP 5:** Enter test fix loop - prove stability
- [ ] **STEP 6:** Create PR and close issue

## Next Actions

**IMMEDIATE:** Move to Step 1 - Discover existing tests protecting against breaking changes from SSOT refactor

**PRIORITY:** Focus on Golden Path stability - users login → get AI responses