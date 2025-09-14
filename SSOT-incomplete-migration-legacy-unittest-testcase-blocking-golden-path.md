# SSOT-incomplete-migration-legacy-unittest-testcase-blocking-golden-path

**Issue:** #1097  
**GitHub URL:** https://github.com/netra-systems/netra-apex/issues/1097  
**Created:** 2025-09-14  
**Status:** DISCOVERY COMPLETE - PLANNING PHASE

## Problem Statement

**CRITICAL VIOLATION:** 10 mission-critical test files are using legacy `unittest.TestCase` instead of required SSOT base classes, compromising Golden Path testing reliability and blocking $500K+ ARR functionality validation.

## Files Requiring Migration

### Priority 1 - Mission Critical Files
1. `tests/unit/services/test_rate_limiter_redis_import_issue_517.py` (Lines 40, 48-50)
2. `tests/mission_critical/test_ssot_test_infrastructure_violations.py` (Lines 34, 119, 150, 176, 204, 230, 340)
3. `test_framework/websocket_handshake_test_utilities.py` (Multiple mock factory violations)

### Additional Files Identified
- 7+ additional test files with direct pytest usage
- 15-20 test files with unittest.TestCase inheritance
- Multiple WebSocket testing utilities with duplicate mock patterns

## SSOT Requirements Violated

- ❌ BaseTestCase SSOT: Tests must inherit from `SSotBaseTestCase` or `SSotAsyncTestCase`
- ❌ Mock Factory SSOT: All mocks must use `SSotMockFactory` - no duplicate mock implementations
- ❌ Test Runner SSOT: All execution through `tests/unified_test_runner.py` - no direct pytest
- ❌ Environment SSOT: All environment access through `IsolatedEnvironment`

## Business Impact

**Golden Path Functionality at Risk:**
- Test pollution preventing reliable WebSocket event validation (5 critical events)
- Inconsistent test execution patterns across services
- Missing standardized chat functionality testing
- CI/CD pipeline instability blocking deployments

## Work Progress Tracking

### Step 0: SSOT Audit ✅ COMPLETE
- [x] Identified top 3 critical violations
- [x] Created GitHub issue #1097
- [x] Created progress tracking document

### Step 1: Discover and Plan Tests 🔄 IN PROGRESS
- [ ] 1.1 DISCOVER EXISTING: Find tests protecting against SSOT refactor breaking changes
- [ ] 1.2 PLAN ONLY: Plan unit/integration/e2e tests for ideal SSOT state

### Step 2: Execute Test Plan
- [ ] Create 20% new SSOT validation tests
- [ ] Focus on non-docker tests (unit, integration no-docker, e2e staging GCP)

### Step 3: Plan Remediation
- [ ] Plan migration from unittest.TestCase to SSotBaseTestCase
- [ ] Plan consolidation of mock factories to SSotMockFactory
- [ ] Plan removal of direct pytest usage

### Step 4: Execute Remediation
- [ ] Migrate test inheritance patterns
- [ ] Consolidate mock factories
- [ ] Update test execution patterns

### Step 5: Test Fix Loop
- [ ] Run all affected tests
- [ ] Fix any import or startup issues
- [ ] Ensure 100% pass rate

### Step 6: PR and Closure
- [ ] Create PR linking to issue #1097
- [ ] Verify Golden Path functionality restored

## Acceptance Criteria

1. **Zero Legacy Patterns**: All tests inherit from SSOT base classes
2. **Single Mock Factory**: All mocks created through SSotMockFactory
3. **Unified Test Execution**: No direct pytest imports in mission critical tests
4. **Environment Isolation**: All tests use IsolatedEnvironment
5. **Golden Path Validation**: WebSocket events test reliably (5 critical events)
6. **System Stability**: All existing tests continue to pass after migration

## Next Actions

1. **SNST** (Step 1): Spawn sub-agent to discover existing tests and plan SSOT validation
2. Execute planned remediation in atomic commits
3. Validate Golden Path functionality remains stable

---

**Estimated Effort:** 2-3 days for complete SSOT test infrastructure consolidation  
**Priority:** P0 - Blocks Golden Path reliability  
**Business Value:** $500K+ ARR protection through reliable testing infrastructure