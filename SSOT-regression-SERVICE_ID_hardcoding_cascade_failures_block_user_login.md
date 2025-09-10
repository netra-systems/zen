# SSOT-regression-SERVICE_ID hardcoding cascade failures block user login

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/203
**Branch:** develop-long-lived
**Priority:** 🚨 ULTRA CRITICAL - Blocks Golden Path User Login

## SSOT Violation Summary

**Problem:** SERVICE_ID inconsistency between hardcoded "netra-backend" and environment variables causes authentication cascade failures every 60 seconds.

**Impact:** Users cannot login reliably - blocks primary business value (chat functionality).

## Files Affected (77+ locations)

### Critical Files Requiring Fix:
- `/auth_service/auth_core/routes/auth_routes.py` (lines 760, 935) - Hardcoded "netra-backend"
- Multiple backend auth client files using environment variables
- Configuration files with mixed SERVICE_ID patterns

## Root Cause Analysis

1. **Mixed Patterns:** Some files hardcode "netra-backend", others use environment variables
2. **Timing Issues:** 60-second cascade failures when SERVICE_ID values don't match
3. **SSOT Violation:** No single source of truth for SERVICE_ID constant

## SSOT Solution Plan

### Phase 1: Create SSOT Constant File
- Create `/shared/constants/service_identifiers.py` with hardcoded SERVICE_ID
- Define SERVICE_ID = "netra-backend" as immutable constant

### Phase 2: Eliminate Environment Variable Usage  
- Replace all `os.environ.get('SERVICE_ID')` with SSOT constant
- Update auth service validation to use consistent hardcoded value
- Remove SERVICE_ID from environment files

### Phase 3: Consolidate Authentication Patterns
- Remove timestamp suffix patterns causing failures
- Standardize auth validation across services

## Test Strategy

### Existing Tests to Validate:
- Mission critical auth tests must continue passing
- Cross-service authentication flows
- All login scenarios in staging/production

### New Tests Required:
- SERVICE_ID consistency validation test
- Auth cascade failure regression test  
- Cross-service SERVICE_ID verification test

## Success Criteria

- ✅ All 77+ SERVICE_ID references use single SSOT constant
- ✅ Authentication cascade failures eliminated
- ✅ Users can login reliably without 60-second retry loops
- ✅ All existing tests pass with SSOT changes
- ✅ Golden path user flow: login → AI responses works consistently

## Work Progress

### Step 0: Discovery ✅ COMPLETED
- Discovered SERVICE_ID SSOT violation through codebase audit
- Created GitHub issue #203 and local tracker

### Step 1: Test Discovery and Planning (NEXT)
- Find existing tests protecting auth functionality
- Plan new tests for SSOT validation
- Ensure test coverage for SERVICE_ID consistency

### Step 2-6: Implementation and Validation (PENDING)
- Execute test plan
- Plan and execute SSOT remediation
- Validate all changes pass tests
- Create PR for review

## Notes

- FIRST DO NO HARM: Ensure auth functionality remains stable during migration
- Focus on atomic commits that don't break existing system state
- Validate each change against golden path user flow