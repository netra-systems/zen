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

## Test Discovery & Strategy (STEP 1)

### Existing Tests Discovered (16 Critical Files)
- **5 Mission Critical** - JWT bypass/SSOT compliance detection
- **6 Integration** - JWT extraction and auth flow validation  
- **3 Unit** - Competing auth implementation detection
- **2 E2E/Staging** - End-to-end JWT authentication flows

### Key SSOT Violations in Tests
1. **UserContextExtractor** - Multiple JWT validation paths with fallbacks
2. **UnifiedWebSocketAuth** - Legacy remediation authentication paths
3. **AuthIntegration** - Local JWT validation vs SSOT delegation

**Target SSOT:** `/auth_service/auth_core/core/jwt_handler.py` - `JWTHandler.validate_token()`

### Test Strategy Plan
- **60% Existing Test Updates** - 15 files need updates for single auth path
- **20% New SSOT Tests** - 4 new files for SSOT compliance validation  
- **20% Execution Strategy** - Unit/Integration/E2E staging (no Docker)
- **47 JWT decode mocks** require replacement with SSOT delegation

### Test Execution (No Docker Required)
- Unit tests: Direct execution with mocks
- Integration: Staging GCP environment 
- E2E: Staging deployment validation
- Mission Critical: Mocked or real services

## Work Progress

- [x] **STEP 0:** SSOT audit completed - Critical P0 violation identified
- [x] **STEP 0.2:** GitHub issue #525 created and local tracking file established
- [x] **STEP 1:** Discover and plan tests - 16 test files identified, comprehensive strategy created
- [ ] **STEP 2:** Execute test plan for new SSOT tests  
- [ ] **STEP 3:** Plan SSOT remediation
- [ ] **STEP 4:** Execute SSOT remediation plan
- [ ] **STEP 5:** Enter test fix loop - prove stability
- [ ] **STEP 6:** Create PR and close issue

## Next Actions

**IMMEDIATE:** Move to Step 2 - Execute test plan for 20% new SSOT-focused tests

**PRIORITY:** Golden Path protection during SSOT consolidation