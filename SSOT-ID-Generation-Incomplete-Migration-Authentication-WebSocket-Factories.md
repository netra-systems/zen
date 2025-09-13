# SSOT-ID-Generation-Incomplete-Migration-Authentication-WebSocket-Factories

**GitHub Issue**: #841
**Priority**: P0 - BLOCKS GOLDEN PATH
**Status**: In Progress - Step 1 Complete

## Issue Summary
20+ critical files still using `uuid.uuid4()` instead of UnifiedIdGenerator SSOT, causing race conditions, ID collisions, and user isolation failures in Golden Path.

## Critical Files Identified
1. `netra_backend/app/auth_integration/auth.py:160` - Session ID generation
2. `netra_backend/app/websocket_core/unified_websocket_auth.py:1303` - Connection ID generation
3. `netra_backend/app/factories/redis_factory.py:594` - Client ID generation
4. `netra_backend/app/factories/clickhouse_factory.py:522` - Client ID generation
5. `netra_backend/app/schemas/audit_models.py:41` - Audit record IDs

## Business Impact
- **Revenue Risk**: $500K+ ARR at risk
- **Security**: Potential cross-user data leakage from ID collisions
- **User Experience**: Authentication and WebSocket connection failures

## Progress Log

### Step 0 - SSOT Audit Complete ✅
- [x] Discovered critical SSOT violation
- [x] Created GitHub issue #841
- [x] Created tracking file
- [x] Ready for step 1 - Test Discovery

### Step 1 - Discover and Plan Tests ✅
- [x] Find existing tests protecting against SSOT ID generation changes
- [x] Plan new tests to validate SSOT compliance
- [x] Update tracking file

#### 1.1 Existing Tests Discovered (Must Continue to Pass):
- **Authentication ID Tests**: 4 critical test files including Golden Path auth flows
- **WebSocket Connection Tests**: 4 critical files including mission critical events suite ($500K+ ARR)
- **Factory Pattern Tests**: 3 files covering user isolation and SSOT compliance
- **ID Migration Tests**: 3 existing files designed for migration validation
- **User Isolation Tests**: 4 files protecting multi-user security
- **Total Coverage**: ~75 WebSocket, ~50 auth, ~30 factory pattern existing tests

#### 1.2 New Test Plan Designed (20% new, 60% existing validation, 20% updates):
**Phase 1 - Reproduction Tests (Failing Before Fix):**
- 4 violation detection test files targeting lines 160, 1303, 594, 522, 41
- Expected to fail before migration, pass after UnifiedIdGenerator adoption

**Phase 2 - SSOT Migration Validation:**
- 4 UnifiedIdGenerator adoption validation test files
- Integration and E2E staging tests for cross-service consistency

**Phase 3 - Business Value Protection:**
- 2 mission critical Golden Path protection test files
- 2 performance impact and concurrent safety test files

**Test Distribution:**
- 12 new test files (~20%)
- 35 existing test files to validate (~60%)
- 8 test files to update (~20%)

**Success Criteria:** All uuid.uuid4() violations detected before fix, Golden Path functionality preserved after migration

### Step 2 - Execute New Test Plan (PENDING)
- [ ] Create new SSOT validation tests
- [ ] Run non-docker tests only
- [ ] Verify tests fail appropriately before fix

### Step 3 - Plan SSOT Remediation (PENDING)
- [ ] Plan UnifiedIdGenerator migration strategy
- [ ] Identify all uuid.uuid4() usage
- [ ] Plan atomic commit strategy

### Step 4 - Execute Remediation (PENDING)
- [ ] Replace uuid.uuid4() calls with UnifiedIdGenerator
- [ ] Validate user isolation maintained
- [ ] Run all tests

### Step 5 - Test Fix Loop (PENDING)
- [ ] Run all affected tests
- [ ] Fix any breaking changes
- [ ] Verify Golden Path functionality

### Step 6 - PR and Closure (PENDING)
- [ ] Create pull request
- [ ] Link to issue #841 for auto-close
- [ ] Merge after review

## Definition of Done
- [ ] All uuid.uuid4() calls replaced with UnifiedIdGenerator
- [ ] User isolation tests passing
- [ ] Golden Path authentication flow working
- [ ] WebSocket connections using consistent ID generation
- [ ] No cross-user data leakage in tests