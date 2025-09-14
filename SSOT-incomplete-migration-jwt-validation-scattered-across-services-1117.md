# SSOT-incomplete-migration-jwt-validation-scattered-across-services

**GitHub Issue:** #1117  
**Created:** 2025-09-14  
**Status:** Step 0 - Discovery Complete  
**Priority:** P0 - Critical Golden Path Blocker  

## Problem Summary

Despite previous JWT SSOT work (issue #670), new audit reveals JWT token validation still scattered across multiple services instead of using single source of truth, blocking user authentication in Golden Path flow.

## Files Involved
- `/auth_service/auth_core/core/jwt_handler.py:29` - JWTHandler class (SSOT)
- `/auth_service/services/jwt_service.py:16` - JWTService wrapper class  
- `/netra_backend/app/auth_integration/auth.py:117` - validate_token_jwt() call
- `/netra_backend/app/websocket_core/unified_websocket_auth.py:1` - WebSocket-specific auth wrapper

## Golden Path Impact
JWT validation failures prevent user login step, blocking entire user login ’ AI response flow.

## Process Status

### Step 0: Discovery  COMPLETE
- [x] SSOT audit completed 
- [x] GitHub issue #1117 created
- [x] Local tracking file created
- [x] Noted relationship to previously resolved issue #670

### Step 1: Discover and Plan Tests (NEXT)
- [ ] 1.1 Discover existing tests
- [ ] 1.2 Plan new SSOT validation tests

### Step 2: Execute Test Plan  
- [ ] Create new SSOT tests for JWT validation

### Step 3: Plan Remediation
- [ ] Plan SSOT consolidation strategy  

### Step 4: Execute Remediation
- [ ] Implement SSOT consolidation

### Step 5: Test Fix Loop
- [ ] Validate all tests pass
- [ ] Fix any breaking changes

### Step 6: PR and Closure
- [ ] Create pull request
- [ ] Link to close issue

## Notes
- Following auth SSOT compliance per reports/auth/BACKEND_AUTH_SSOT_AUDIT_20250107.md
- Auth service MUST be the ONLY source for JWT operations
- Previous work in issue #670 may have missed some violations found in 2025-09-14 audit
- Eliminate wrapper classes and duplicate validation pathways