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

### Step 1: Test Discovery and Planning ✅ COMPLETED

#### 1.1 EXISTING TESTS DISCOVERED (60% of work)
**Mission Critical Protection Tests (Must Continue Passing):**
- `/tests/mission_critical/test_staging_auth_cross_service_validation.py` - Cross-service auth validation
- `/tests/mission_critical/test_websocket_agent_events_suite.py` - Agent auth integration  
- `/auth_service/tests/test_service_authentication.py` - SERVICE_ID validation logic
- `/netra_backend/tests/auth/test_auth_integration.py` - Backend auth client tests
- `/tests/e2e/test_auth_backend_desynchronization.py` - Service sync validation

**Key Findings:**
- 77+ locations with SERVICE_ID inconsistency identified
- 15+ mission-critical auth tests protecting current functionality
- Tests validate hardcoded "netra-backend" vs environment variable patterns
- Cross-service authentication heavily tested but with mixed SERVICE_ID sources

#### 1.2 NEW TEST PLAN (20% of work)
**FAILING Tests (Expose Current SSOT Violation):**
1. `test_service_id_ssot_violation_detection.py` - Detect mixed hardcoded vs env patterns
2. `test_service_id_cross_service_inconsistency.py` - Expose auth/backend SERVICE_ID mismatches
3. `test_service_id_environment_cascade_failure.py` - Reproduce 60-second auth failures

**PASSING Tests (Validate Ideal SSOT State):**
1. `test_service_id_ssot_compliance.py` - Validate single source of truth
2. `test_service_id_hardcoded_consistency.py` - Verify all services use same constant
3. `test_service_id_auth_flow_stability.py` - Confirm auth works with SSOT
4. `test_service_id_environment_independence.py` - Validate independence from env vars
5. `test_golden_path_post_ssot_remediation.py` - End-to-end login → AI responses

**Test Execution Strategy:**
- Unit tests: Configuration validation (no Docker)
- Integration tests: Localhost services (no Docker) 
- E2E tests: Staging GCP remote environment

#### 1.3 RISK ASSESSMENT
**CRITICAL RISKS:**
- Environment-based SERVICE_ID (staging/production) causes auth failures
- Blocks $500K+ ARR chat functionality
- 60-second cascade failure pattern affects user experience

**MITIGATION:**
- SSOT approach eliminates environment dependency
- Maintains backward compatibility during transition
- All existing tests must pass post-refactor

### Step 2-6: Implementation and Validation (PENDING)
- Execute test plan
- Plan and execute SSOT remediation
- Validate all changes pass tests
- Create PR for review

## Notes

- FIRST DO NO HARM: Ensure auth functionality remains stable during migration
- Focus on atomic commits that don't break existing system state
- Validate each change against golden path user flow